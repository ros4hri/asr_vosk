#!/usr/bin/env python3
# Copyright (c) 2022 PAL Robotics S.L. All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
#
#  1. Redistributions of source code must retain the above copyright notice,
#  this list of conditions and the following disclaimer.
#  2. Redistributions in binary form must reproduce the above copyright notice,
#  this list of conditions and the following disclaimer in the documentation
#  and/or other materials provided with the distribution.
#  3. Neither the name of the copyright holder nor the names of its
#  contributors may be used to endorse or promote products derived from this
#  software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
#  IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
#  TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
#  PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# Code based on LuxAI work:
# https://github.com/luxai-qtrobot/software/blob/master/apps/qt_vosk_app

# Copyright (c) 2021-2022 LuxAI All rights reserved.

from pathlib import Path
import queue
import time
import rospy
import rospkg
import json
import vosk
from threading import Thread

from std_msgs.msg import Bool
from audio_common_msgs.msg import AudioData
from hri_msgs.msg import IdsList, LiveSpeech

from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue

from pal_interaction_msgs.msg import TtsActionGoal, TtsActionResult
from language_center_msgs.msg import SetLocaleResult, SetLocaleAction
import actionlib

# available Vosk model size, **ordered by preference**
MODEL_SIZES = ["large", "small"]


class VoskSpeech(Thread):
    """Vosk speech recognition"""

    DIAGNOSTICS_BASENAME = "Interaction: Speech recognition"

    def __init__(self):
        super(VoskSpeech, self).__init__()

        self.diag_pub = rospy.Publisher("/diagnostics", DiagnosticArray, queue_size=1)

        self.is_kaldi_recognizing = False
        self.audio_data_queue = queue.Queue(maxsize=2000)  # more than one minute
        self.audio_rate = rospy.get_param("/vosk_asr/audio_rate", 16000)
        self.default_language = rospy.get_param("/vosk_asr/default_language", "en_US")

        self._set_locale_as = actionlib.SimpleActionServer(
            "/asr/set_locale",
            SetLocaleAction,
            execute_cb=self.set_locale,
            auto_start=False,
        )

        # if model_size not set, look for available models size, in the order
        # of preference set in MODEL_SIZES
        self.model_size = rospy.get_param("/vosk_asr/model_size", None)

        model_path_param = rospy.get_param("/vosk_asr/vosk_model_path", "")

        if model_path_param:
            self.model_path = Path(model_path_param)
        else:
            try:
                self.model_path = Path(
                    rospkg.RosPack().get_path("vosk_language_models")
                )
            except rospkg.common.ResourceNotFound:
                rospy.logfatal(
                    "Can not find the Vosk language models! the "
                    "vosk_language_models ROS package is not installed, and "
                    "parameter /vosk_asr/vosk_model_path is not provided."
                )
                rospy.signal_shutdown("vosk models path not found. Shutting down.")
                return

        self.speech_goal = LiveSpeech()

        self.model = None

        model_ok, _ = self.load_model(self.default_language, self.model_size)
        if not model_ok:
            rospy.signal_shutdown("vosk model not available. Shutting down.")
            return

        self.enable_hotword = True

        self.pub_voices = rospy.Publisher(
            "/humans/voices/tracked", IdsList, queue_size=1
        )

        self.pub_speech = rospy.Publisher(
            "/humans/voices/anonymous_speaker/speech", LiveSpeech, queue_size=10
        )
        self.pub_voice_audio = rospy.Publisher(
            "/humans/voices/anonymous_speaker/audio", AudioData, queue_size=10
        )
        self.pub_is_speaking = rospy.Publisher(
            "/humans/voices/anonymous_speaker/is_speaking", Bool, queue_size=10
        )
        rospy.Subscriber("/audio/channel0", AudioData, self.callback_audio_stream)
        rospy.Subscriber("/audio/voice_detected", Bool, self.on_voice_detected)
        rospy.Subscriber("/tts/goal", TtsActionGoal, self.tts_start)
        rospy.Subscriber("/tts/result", TtsActionResult, self.tts_end)
        self.cout_speaking = 0
        self.max_no_voice = 1
        self.user_is_speaking = False
        self.robot_speaking = False

        self._set_locale_as.start()

        rospy.loginfo("ASR Vosk action servers ready")

        # immediately start recognising speech
        self.listen = True
        rospy.Timer(rospy.Duration(1), self.publish_diagnostics)

        # start the background thread
        self.running = True
        self.start()

    def stop(self):
        rospy.loginfo("Stopping Vosk thread...")
        self.running = False

    def load_model(self, language, model_size=None):

        model_sizes = [model_size] + MODEL_SIZES if model_size else MODEL_SIZES

        model_loaded = False
        msg = ""

        if not self.model_path.exists():
            msg = "Vosk models path %s does not exists" % self.model_path
            rospy.logerr(msg)
            return model_loaded, msg

        model_path = self.model_path / language

        if not model_path.exists():
            # look for language fallbacks
            for lang in self.model_path.iterdir():
                if str(lang.name).split("_")[0] == str(language).split("_")[0]:
                    rospy.logwarn(
                        "Desired language <%s> not available. Falling back to variant <%s>"
                        % (language, lang.name)
                    )
                    language = lang
                    break

        for size in model_sizes:

            model_path = self.model_path / language / size
            if model_path.exists():
                if self.model_size and size != self.model_size:
                    rospy.logwarn(
                        "Desired model size <%s> not available. Falling back to <%s>"
                        % (self.model_size, size)
                    )
                self.model = vosk.Model(str(model_path))

                msg = "Vosk model loaded: %s" % model_path
                rospy.loginfo(msg)
                model_loaded = True

        if not model_loaded:
            msg = "Vosk model not found! I was looking for one of %s in %s" % (
                model_sizes,
                self.model_path / language,
            )
            rospy.logerr(msg)

        return model_loaded, msg

    def set_locale(self, act):
        rospy.loginfo("Changing ASR language to %s..." % act.locale)
        self.listen = False

        result = SetLocaleResult()

        ok, msg = self.load_model(act.locale)
        result.ok = ok
        result.error_msg = msg

        self._set_locale_as.set_succeeded(result)

        rospy.loginfo("Language model loaded, starting speech recognition.")
        self.listen = True

    def tts_start(self, msg):
        self.robot_speaking = True

    def tts_end(self, msg):
        self.robot_speaking = False

    def run(self):
        """
        background thread which waits for any speech detection and processes it with Kaldi
        """
        rospy.loginfo("started Vosk")

        while self.running:

            if self.listen:  # only process if listen is set to true
                transcript = self.recognize_kaldi(
                    timeout=10, options=[], clear_queue=True
                ).strip()

                if transcript:

                    rospy.loginfo('Vosk recognised text "%s"' % transcript)

                    self.speech_goal.incremental = transcript
                    self.speech_goal.final = transcript

                    if (not self.robot_speaking) and (
                        len(self.speech_goal.incremental) != 0
                    ):
                        self.pub_speech.publish(self.speech_goal)
                        rospy.loginfo(self.speech_goal)

            else:
                time.sleep(0.01)

            # rospy.loginfo("preempt called")

    def on_voice_detected(self, speech):

        if speech.data != self.user_is_speaking:
            self.user_is_speaking = speech.data
            if not self.user_is_speaking:
                self.speech_goal = LiveSpeech()

            self.pub_voices.publish(IdsList(ids=["anonymous_speaker"]))
            self.pub_is_speaking.publish(Bool(data=self.user_is_speaking))

    def callback_audio_stream(self, msg):
        indata = bytes(msg.data)
        try:
            self.audio_data_queue.put_nowait(indata)

        except BaseException:
            pass

        # check if user is speaking in order to publish speech audio and start
        # recognising if not done already
        if self.user_is_speaking:
            # publish speech audio data while recognising
            self.pub_voice_audio.publish(msg.data)

    """
        ros speech recognize callback
    """

    def contains_options(self, options, transcript):
        if not transcript:
            return None
        for opt in options:
            opt = opt.strip()
            # do not split the transcript of an option contains more than a
            # word such as 'blue color'
            phrase = transcript if (len(opt.split()) > 1) else transcript.split()
            if opt and opt in phrase:
                return opt
        return None

    def recognize_kaldi(self, timeout, options, clear_queue=False):

        if self.audio_data_queue.empty():
            # no data yet? sleep a tiny bit (to avoid a busy wait) and return
            time.sleep(0.01)
            return ""

        self.is_kaldi_recognizing = True
        if clear_queue:
            # example : if audio rate is 16000 and respeaker buffersize is 512,
            # then the last one second will be around 31 item in queue
            while self.audio_data_queue.qsize() > int(self.audio_rate / 512 / 2):
                self.audio_data_queue.get()
                if self.listen == False:
                    break

        if options:
            rec = vosk.KaldiRecognizer(
                self.model, self.audio_rate, json.dumps(options, ensure_ascii=False)
            )
        else:
            rec = vosk.KaldiRecognizer(self.model, self.audio_rate)

        t_start = time.time()

        # rec.SetWords(True)
        # rec.SetPartialWords(True)

        transcript = ""

        self.speech_audio = LiveSpeech()

        while not (self.robot_speaking and self.listen):
            data = self.audio_data_queue.get()

            if rec.AcceptWaveform(data):
                result = rec.Result()
                jres = json.loads(result)
                transcript = jres["text"].strip()
                if transcript:
                    break
            else:
                result = rec.PartialResult()
                jres = json.loads(result)
                partial = jres["partial"]

                if (partial != self.speech_goal.incremental) and (partial != ""):

                    self.speech_goal.incremental = partial
                    self.speech_goal.final = ""
                    self.pub_speech.publish(self.speech_goal)
                    transcript = partial

                word = self.contains_options(options, partial)
                if word:
                    transcript = word
                    break

            # check the timeout
            if ((time.time() - t_start) > timeout) or not self.user_is_speaking:
                break

        self.user_is_speaking = False
        self.is_kaldi_recognizing = False
        return transcript

    def publish_diagnostics(self, evt):

        arr = DiagnosticArray()

        msg = DiagnosticStatus(
            level=DiagnosticStatus.OK,
            name=self.DIAGNOSTICS_BASENAME,
            message="vosk ASR running",
            values=[
                KeyValue(key="Package name", value="vosk_asr"),
                KeyValue(key="Last recognised sentence", value=self.speech_goal.final),
            ],
        )

        arr.header.stamp = rospy.Time.now()
        arr.status = [msg]
        self.diag_pub.publish(arr)


if __name__ == "__main__":
    rospy.init_node("vosk_recognizer")
    speech = VoskSpeech()
    if speech.is_alive():
        rospy.loginfo("vosk_recognizer is ready!")
        rospy.spin()
        speech.stop()
        speech.join()
        rospy.loginfo("vosk_recognizer shutdown")
