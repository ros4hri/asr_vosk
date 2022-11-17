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

import os
import queue
import time
import rospy
import json
import vosk
from threading import Thread, Condition

from std_msgs.msg import String, Bool
from audio_common_msgs.msg import AudioData
from vosk_asr.srv import StartASR, StopASR, StartASRResponse, StopASRResponse
from hri_msgs.msg import LiveSpeech
from pal_interaction_msgs.msg import TtsActionGoal, TtsActionResult


class VoskSpeech(Thread):
    """Vosk speech rcognition"""

    def __init__(self):
        super(VoskSpeech, self).__init__()

        self.is_kaldi_recognizing = False
        self.audio_data_queue = queue.Queue(
            maxsize=2000)  # more than one minute
        self.audio_rate = rospy.get_param("/vosk_asr/audio_rate", 16000)
        self.language = rospy.get_param("/vosk_asr/default_language", 'en_US')
        self.user_is_speaking = False
        self.model_path = rospy.get_param("/vosk_asr/vosk_model_path", "/opt/pal/gallium/share/vosk_language_models/")
        self.default_dir = "/opt/pal/gallium/share/vosk_language_models/"
        self.user_speaks = Bool()
        self.speech_goal = LiveSpeech()
        self.model = vosk.Model(self.model_path +self.language + "/small") #by default use large database of english
        self.enable_hotword = True
        self.pub_speech = rospy.Publisher(
            '/humans/voices/anonymous_speaker/speech',
            LiveSpeech,
            queue_size=10)
        self.pub_voice_audio = rospy.Publisher(
            '/humans/voices/anonymous_speaker/audio', AudioData, queue_size=10)
        self.pub_is_speaking = rospy.Publisher(
            '/humans/voices/anonymous_speaker/is_speaking', Bool, queue_size=10)
        # start recognize service
        self.start_asr = rospy.Service(
            '/vosk_asr/start', StartASR, self.start_recognizing)
        self.stop_asr = rospy.Service(
            '/vosk_asr/stop', StopASR, self.stop_recognizing)
        rospy.Subscriber('/audio', AudioData, self.callback_audio_stream)
        rospy.Subscriber('/is_speeching', Bool, self.user_speaking)
        rospy.Subscriber('/tts/goal', TtsActionGoal, self.tts_start)
        rospy.Subscriber('/tts/result', TtsActionResult, self.tts_end)
        self.cout_speaking = 0
        self.max_no_voice = 1
        self.user_is_speaking = False
        self.robot_speaking = False
        # start the background thread
        self.listen = False
        self.start()

    def start_recognizing(self, act):
        self.listen = True
        model_name = act.language #need to convert it as models are stored in format vosk_language_model_en_us_large, small letters
        if not (os.path.exists(self.model_path+model_name)): #if en_US package does not exist for instance
          for file in os.listdir(self.model_path):
            main_lang = (act.language).split("_")[0]
            if main_lang in file: #if "en" is in subdir "en_GB"
              self.model_path = self.model_path + file #get full path

        else:
           self.model_path = self.model_path+model_name
        if (os.path.exists(self.model_path+"/large")): #check if large database exists
          self.model_path += "/large"
          self.model = vosk.Model(self.model_path)
          self.language = act.language
          rospy.loginfo("started listening in language: " + act.language)
          return (StartASRResponse(True))
        elif (os.path.exists(self.model_path+"/small")):
          self.model_path+="/small"
          self.model = vosk.Model(self.model_path)
          self.language = act.language
          rospy.loginfo("started listening in language: " + act.language)
          return (StartASRResponse(True))
        else:
          rospy.loginfo("Checking in opt/pal/gallium/share/vosk_language_models directory")
          if not (os.path.exists(self.default_dir+model_name)): #if en_US package does not exist for instance
            for file in os.listdir(self.default_dir):
              main_lang = (act.language).split("_")[0]
              if main_lang in file: #if "en" is in subdir "en_GB"
                self.default_dir = self.default_dir + file #get full path
          else:
             self.default_dir = self.default_dir+model_name
             rospy.loginfo("model found")

          if (os.path.exists(self.default_dir+"/large")): #check if large database exists
            self.default_dir += "/large"
            self.model = vosk.Model(self.default_dir)
            self.language = act.language
            rospy.loginfo("started listening in language: " + act.language)
            return (StartASRResponse(True))
          elif (os.path.exists(self.default_dir+"/small")):
            self.default_dir+="/small"
            self.model = vosk.Model(self.default_dir)
            self.language = act.language
            rospy.loginfo("started listening in language: " + act.language)
            return (StartASRResponse(True))
          else:
            rospy.logerr("no available language")
            return (StartASRResponse(False))

    def stop_recognizing(self, srv):
        self.listen = False
        rospy.loginfo("stopping listening")
        return (StopASRResponse(True))

    def tts_start(self, msg):
        self.robot_speaking = True

    def tts_end(self, msg):
        self.robot_speaking = False

    def run(self):
        """
        background thread which waits for any speech detection and processes it with Kaldi
        """
        rospy.loginfo("started vosk")
        while not rospy.is_shutdown():
            if rospy.is_shutdown():
                break
            if (self.listen == True):  # only process if listen is set to true
                transcript = self.recognize_kaldi(10, [], clear_queue=True)
                rospy.logdebug(transcript)
                if transcript:
                    self.speech_goal.incremental = transcript
                    self.speech_goal.final = transcript
                    if ((not self.robot_speaking) and (
                            len(self.speech_goal.incremental) != 0)):
                        self.pub_speech.publish(self.speech_goal)
                        rospy.loginfo(self.speech_goal)
            #rospy.loginfo("preempt called")

    def user_speaking(self, speech):
        if (speech.data):
            self.user_is_speaking = True
        if(self.user_is_speaking):
            if (not speech.data) and (self.cout_is_speak <
                                      self.max_no_voice):  # 6 continuous no speaking
                self.cout_is_speak += 1
            elif speech.data:
                self.cout_is_speak = 0  # restart counter if again a speech detected is seen
            else:
                self.user_is_speaking = False
                self.speech_goal = LiveSpeech()
        self.user_speaks.data = self.user_is_speaking
        self.pub_is_speaking.publish(self.user_speaks)

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
    def recognize_kaldi(self, timeout, options, clear_queue=False):
        self.is_kaldi_recognizing = True
        if clear_queue:
            # example : if audio rate is 16000 and respeaker buffersize is 512,
            # then the last one second will be around 31 item in queue
            while self.audio_data_queue.qsize() > int(self.audio_rate / 512 / 2):
                self.audio_data_queue.get()
                if (self.listen == False):
                    break

        if options:
            rec = vosk.KaldiRecognizer(
                self.model, self.audio_rate, json.dumps(
                    options, ensure_ascii=False))
        else:
            rec = vosk.KaldiRecognizer(self.model, self.audio_rate)

        t_start = time.time()
        rec.SetWords(True)
       # rec.SetPartialWords(True)
        transcript = ''
        self.speech_audio = LiveSpeech()
        while not (self.robot_speaking and self.listen == True):
            data = self.audio_data_queue.get()

            if rec.AcceptWaveform(data):
                result = rec.Result()
                jres = json.loads(result)
                transcript = jres['text'].strip()
                if transcript:
                    break
            else:
                result = rec.PartialResult()
                jres = json.loads(result)
                partial = jres['partial']
                self.user_speaks.data = True

                if ((partial != self.speech_goal.incremental)
                        and (partial != "")):

                    self.speech_goal.incremental = partial
                    self.speech_goal.final = ""
                    self.pub_speech.publish(self.speech_goal)
                word = self.contains_options(options, partial)
                if word:
                    transcript = word
                    break
            # check the timeout
            if ((time.time() - t_start) >
                    timeout) or (self.user_is_speaking == False):
                transcript = ''
                break
        self.user_is_speaking = False
        self.is_kaldi_recognizing = False
        return transcript


if __name__ == "__main__":
    rospy.init_node('vosk_recognizer')
    speech = VoskSpeech()
    rospy.loginfo("vosk_recognizer is ready!")
    rospy.spin()
    rospy.loginfo("vosk_recognizer shutdown")
