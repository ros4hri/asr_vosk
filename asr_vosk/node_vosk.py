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
import json
from lifecycle_msgs.msg import State
from pal_tts_msgs.action import TTS
from rcl_interfaces.msg import ParameterDescriptor
import rclpy
from rclpy.executors import SingleThreadedExecutor, ExternalShutdownException
from rclpy.lifecycle import Node, LifecycleState, TransitionCallbackReturn
from std_msgs.msg import Bool
from vosk import Model, KaldiRecognizer
import yaml


class NodeVosk(Node):
    """Vosk speech recognition node."""

    def __init__(self):
        super().__init__('asr_vosk')

        resource_type = 'asr.vosk.model'
        self.available_models = defaultdict(dict)
        for pkg in get_resources(resource_type).keys():
            pkg_share_path = get_package_share_path(pkg)
            cfg_file_path = pkg_share_path / get_resource(resource_type, pkg)[0]
            with open(cfg_file_path, 'r') as f:
                cfg = yaml.safe_load(f)
                self.available_models[cfg['locale']][cfg['size']] = pkg_share_path / cfg['path']

        self.declare_parameter(
            'audio_rate', 16000, ParameterDescriptor(description='Device sampling rate'))
        self.declare_parameter(
            'locale', "en_US", ParameterDescriptor(description='Regional language locale'))
        self.declare_parameter(
            'model_size', "small", ParameterDescriptor(description='Model size [small, large]'))
        self.declare_parameter(
            'supported_locales', list(self.available_models.keys()), ParameterDescriptor(
                description='Supported regional languages locales', read_only=True))

        self.get_logger().info('State: Unconfigured.')

    def __del__(self):
        state = self._state_machine.current_state
        self.on_shutdown(LifecycleState(state_id=state[0], label=state[1]))

    def on_cleanup(self, state: LifecycleState) -> TransitionCallbackReturn:
        self.internal_cleanup()
        self.get_logger().info('State: Unconfigured.')
        return super().on_cleanup(state)

    def on_configure(self, state: LifecycleState) -> TransitionCallbackReturn:
        self.locale = self.get_parameter('locale').value
        audio_rate = self.get_parameter('audio_rate').value
        model_size = self.get_parameter('model_size').value

        try:
            model_path = str(self.available_models[self.locale][model_size])
            self.model = Model(model_path)
            self.get_logger().info(f'Loaded {self.locale} {model_size} model')
        except Exception as e:  # vosk Model raises generic exceptions :/
            self.get_logger().error(f'Failed to load {self.locale} {model_size} model: {str(e)}')
            return TransitionCallbackReturn.FAILURE

        self.recognizer = KaldiRecognizer(self.model, audio_rate)

        self.get_logger().info('State: Inactive.')
        return super().on_configure(state)

    def on_deactivate(self, state: LifecycleState) -> TransitionCallbackReturn:
        self.internal_deactivate()
        self.get_logger().info('State: Inactive.')
        return super().on_deactivate(state)

    def on_activate(self, state: LifecycleState) -> TransitionCallbackReturn:
        self.listening = True
        self.current_incremental = ''
        self.last_final = ''

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
            AudioData, "/audio/channel0", self.on_audio_data, 10)
        self.voice_detected_sub = self.create_subscription(
            Bool, "/audio/voice_detected", self.on_voice_detected, 1)
        self.tts_goal_sub = self.create_subscription(
            TTS.Goal, "/tts/goal", self.on_tts_goal, 1)
        self.tts_result_sub = self.create_subscription(
            TTS.Result, "/tts/result", self.on_tts_result, 1)

        self.diag_timer = self.create_timer(1., self.publish_diagnostics)

        # currently the voice is always associated to the same anonymous speaker
        self.voices_pub.publish(IdsList(ids=["anonymous_speaker"]))

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
        del self.model

    def internal_deactivate(self):
        self.destroy_timer(self.diag_timer)
        self.destroy_subscription(self.audio_data_sub)
        self.destroy_subscription(self.voice_detected_sub)
        self.destroy_subscription(self.tts_goal_sub)
        self.destroy_subscription(self.tts_result_sub)
        self.destroy_publisher(self.diag_pub)
        self.destroy_publisher(self.voices_pub)
        self.destroy_publisher(self.speech_pub)
        self.destroy_publisher(self.voice_audio_pub)
        self.destroy_publisher(self.is_speaking_pub)

    def on_tts_goal(self, _):
        self.listening = False
        self.last_incremental = ''
        self.recognizer.Reset()

    def on_tts_result(self, _):
        self.listening = True

    def on_voice_detected(self, msg):
        self.is_speaking_pub.publish(msg)

    def on_audio_data(self, audio_data_msg):
        self.voice_audio_pub.publish(audio_data_msg)

        if self.listening:
            speech_msg = LiveSpeech(language=self.locale, confidence=1.)
            speech_msg.header.stamp = self.get_clock().now().to_msg()

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

    def publish_diagnostics(self):
        arr = DiagnosticArray()
        msg = DiagnosticStatus(
            level=DiagnosticStatus.OK,
            name="Interaction: Speech recognition",
            message="vosk ASR running",
            values=[
                KeyValue(key="Package name", value="asr_vosk"),
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
