# Copyright (c) 2024 PAL Robotics S.L. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ament_index_python.packages import get_package_share_path
from ament_index_python.resources import get_resource, get_resources
from audio_common_msgs.msg import AudioData
from collections import defaultdict
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from hri_msgs.msg import IdsList, LiveSpeech
from i18n_msgs.action import SetLocale
from i18n_msgs.srv import GetLocales
import json
from lifecycle_msgs.msg import State
from rcl_interfaces.msg import ParameterDescriptor
import rclpy
from rclpy.action import ActionServer, GoalResponse
from rclpy.executors import SingleThreadedExecutor, ExternalShutdownException
from rclpy.lifecycle import Node, LifecycleState, TransitionCallbackReturn
from rclpy.parameter import Parameter
from std_msgs.msg import Bool
from vosk import Model, KaldiRecognizer
import yaml


class NodeVosk(Node):
    """Vosk speech recognition node."""

    def __init__(self):
        super().__init__('asr_vosk')

        self.declare_parameter(
            'audio_rate', 16000, ParameterDescriptor(description='Device sampling rate'))
        self.declare_parameter(
            'model', "vosk_model_small", ParameterDescriptor(description='Model family name'))
        self.declare_parameter(
            'default_locale', "en_US", ParameterDescriptor(description='Default locale'))

        self.get_logger().info('State: Unconfigured.')

    def __del__(self):
        self.trigger_shutdown()

    def on_cleanup(self, state: LifecycleState) -> TransitionCallbackReturn:
        self.internal_cleanup()
        self.get_logger().info('State: Unconfigured.')
        return super().on_cleanup(state)

    def on_configure(self, state: LifecycleState) -> TransitionCallbackReturn:
        self.audio_rate = self.get_parameter('audio_rate').value
        self.default_locale = self.get_parameter('default_locale').value
        self.model = self.get_parameter('model').value

        # Load available models and set the supported locales accordingly
        resource_type = 'asr.vosk.model'
        self.available_models = defaultdict(dict)
        for pkg in get_resources(resource_type).keys():
            pkg_share_path = get_package_share_path(pkg)
            cfg_file_path = pkg_share_path / get_resource(resource_type, pkg)[0]
            with open(cfg_file_path, 'r') as f:
                cfg = yaml.safe_load(f)
                try:
                    if self.model == cfg['name']:
                        self.available_models[cfg['locale']] = pkg_share_path / cfg['path']
                except KeyError as e:
                    self.get_logger().error(
                        f'Error parsing configuration for package {pkg}: {str(e)}')
                    return TransitionCallbackReturn.FAILURE

        loaded_model, _ = self.load_model(self.default_locale)
        if not loaded_model:
            return TransitionCallbackReturn.FAILURE

        self.get_logger().info('State: Inactive.')
        return super().on_configure(state)

    def on_deactivate(self, state: LifecycleState) -> TransitionCallbackReturn:
        self.internal_deactivate()
        self.get_logger().info('State: Inactive.')
        return super().on_deactivate(state)

    def on_activate(self, state: LifecycleState) -> TransitionCallbackReturn:
        self.current_incremental = ''
        self.last_final = ''
        self.listening = True

        self.diag_pub = self.create_publisher(
            DiagnosticArray, "/diagnostics", 1)
        self.voices_pub = self.create_publisher(
            IdsList, "/humans/voices/tracked", 1)
        self.speech_pub = self.create_publisher(
            LiveSpeech, "/humans/voices/anonymous_speaker/speech", 10)
        self.voice_audio_pub = self.create_publisher(
            AudioData, "/humans/voices/anonymous_speaker/audio", 10)
        self.is_speaking_pub = self.create_publisher(
            Bool, "/humans/voices/anonymous_speaker/is_speaking", 10)

        self.audio_data_sub = self.create_subscription(
            AudioData, "audio/channel0", self.on_audio_data, 10)
        self.voice_detected_sub = self.create_subscription(
            Bool, "audio/voice_detected", self.on_voice_detected, 1)
        self.voice_detected_sub = self.create_subscription(
            Bool, "/robot_speaking", self.on_robot_speaking, 1)

        self.get_supported_locales_server = self.create_service(
            GetLocales, "~/get_supported_locales", self.on_get_supported_locales)

        self.set_default_locale_server = ActionServer(
            self, SetLocale, "~/set_default_locale",
            goal_callback=self.on_set_default_locale_goal,
            execute_callback=self.on_set_default_locale_exec)

        self.diag_timer = self.create_timer(1., self.publish_diagnostics)

        # currently the voice is always associated to the same anonymous speaker
        # publish it repeatedly to ensure latecomers get the message (the topic is not latched)
        def publish_anonymous_voice_id():
            self.voices_pub.publish(IdsList(ids=["anonymous_speaker"]))

        publish_anonymous_voice_id()
        self.voices_timer = self.create_timer(
            1., publish_anonymous_voice_id, clock=self.get_clock())

        self.get_logger().info('State: Active.')
        return super().on_activate(state)

    def on_shutdown(self, state: LifecycleState) -> TransitionCallbackReturn:
        if state.state_id == State.PRIMARY_STATE_ACTIVE:
            self.internal_deactivate()
        if state.state_id in [State.PRIMARY_STATE_ACTIVE, State.PRIMARY_STATE_INACTIVE]:
            self.internal_cleanup()
        self.get_logger().info('State: Finalized.')
        return super().on_shutdown(state)

    def internal_cleanup(self):
        del self.recognizer

    def internal_deactivate(self):
        self.destroy_timer(self.diag_timer)
        del self.set_default_locale_server
        self.destroy_service(self.get_supported_locales_server)
        self.destroy_subscription(self.audio_data_sub)
        self.destroy_subscription(self.voice_detected_sub)
        self.destroy_publisher(self.diag_pub)
        self.destroy_publisher(self.voices_pub)
        self.destroy_publisher(self.speech_pub)
        self.destroy_publisher(self.voice_audio_pub)
        self.destroy_publisher(self.is_speaking_pub)

    def load_model(self, locale):
        try:
            model_path = str(self.available_models[locale])
            model = Model(model_path)
            self.get_logger().info(f'Loaded {self.model} {locale} model')
        except Exception as e:  # vosk Model raises generic exceptions :/
            error_msg = f'Failed to load {self.model} {locale} model: {str(e)}'
            self.get_logger().error(error_msg)
            return False, error_msg

        self.recognizer = KaldiRecognizer(model, self.audio_rate)
        return True, ""

    def on_voice_detected(self, msg):
        self.is_speaking_pub.publish(msg)

    def on_robot_speaking(self, msg):
        self.listening = not msg.data

    def on_audio_data(self, audio_data_msg):
        self.voice_audio_pub.publish(audio_data_msg)

        if self.listening:
            speech_msg = LiveSpeech(locale=self.default_locale, confidence=1.)
            speech_msg.header.stamp = self.get_clock().now().to_msg()

            non_empty_audio_data = False
            for audio_data in audio_data_msg.data:
                if audio_data != 0:
                    non_empty_audio_data = True
                    break

            if non_empty_audio_data or self.current_incremental:
                if self.recognizer.AcceptWaveform(bytes(audio_data_msg.data)):
                    result = json.loads(self.recognizer.Result())
                    text = result["text"].strip()

                    if text:
                        speech_msg.incremental = text
                        speech_msg.final = text
                        self.speech_pub.publish(speech_msg)

                        self.last_final = text

                    self.current_incremental = ''
                else:
                    result = json.loads(self.recognizer.PartialResult())
                    partial = result["partial"]

                    if partial and (partial != self.current_incremental):
                        speech_msg.incremental = partial
                        self.speech_pub.publish(speech_msg)

                    self.current_incremental = partial

    def on_get_supported_locales(self, request, response):
        response.locales = list(self.available_models.keys())
        return response

    def on_set_default_locale_goal(self, goal_request):
        if goal_request.locale in self.available_models:
            return GoalResponse.ACCEPT
        else:
            return GoalResponse.REJECT

    def on_set_default_locale_exec(self, goal_handle):
        locale = goal_handle.request.locale
        result = SetLocale.Result()
        loaded_model, error_msg = self.load_model(locale)
        if loaded_model:
            self.set_parameters([Parameter('default_locale', value=locale)])
            self.default_locale = locale
            goal_handle.succeed()
        else:
            goal_handle.abort()
            result.error_msg = error_msg
        return result

    def publish_diagnostics(self):
        arr = DiagnosticArray()
        msg = DiagnosticStatus(
            level=DiagnosticStatus.OK,
            name="/communication/asr/asr_vosk",
            message="vosk ASR running",
            values=[
                KeyValue(key="Module name", value="asr_vosk"),
                KeyValue(key="Current lifecycle state",
                         value=self._state_machine.current_state[1]),
                KeyValue(key="Model", value=self.model),
                KeyValue(key="Supported locales", value=str(self.available_models.keys())),
                KeyValue(key="Current default_locale", value=self.default_locale),
                KeyValue(key="Currently listening", value=str(self.listening)),
                KeyValue(key="Last recognised sentence", value=self.last_final),
            ],
        )

        arr.header.stamp = self.get_clock().now().to_msg()
        arr.status = [msg]
        self.diag_pub.publish(arr)


def main(args=None):
    rclpy.init(args=args)
    node = NodeVosk()
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        node.destroy_node()


if __name__ == '__main__':
    main()
