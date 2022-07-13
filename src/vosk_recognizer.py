#!/usr/bin/env python3
import os
import queue
import time
import rospy
import json
import vosk
from threading import Thread, Condition

from std_msgs.msg import String, Bool
from audio_common_msgs.msg import AudioData
from vosk_asr.srv import *



class VoskSpeech(Thread):
    """Vosk speech rcognition"""

    def __init__(self):
        super(VoskSpeech, self).__init__()

        self.is_kaldi_recognizing = False
        self.aqueue = queue.Queue(maxsize=2000) # more than one minute 
        self.condition = Condition()

        self.audio_rate = 16000
        self.language = "en_US"
        self.user_is_speaking = False
        self.model_path = '/home/user/ws/src/ros-vosk/model/'
        self.language = ""
        # initialize vosk 
        self.user_speaks = Bool()
        self.model = vosk.Model(self.model_path + self.language)
        self.enable_hotword = True 
        self.recognize_pub = rospy.Publisher('/humans/voices/anonymous_id/speech_final', String, queue_size=10)       
        self.pub_partial = rospy.Publisher('/humans/voices/anonymous_id/speech',String, queue_size=10)
        self.pub_voice_audio = rospy.Publisher('/humans/voices/anonymous_id/audio', AudioData, queue_size=10)
        self.pub_is_speaking = rospy.Publisher('/humans/voices/anonymous_id/is_speaking', Bool, queue_size=10)
        # start recognize service
        self.speech_recognize = rospy.Service('/speech/recognize', speech_recognize, self.callback_recognize)
        rospy.Subscriber('/audio', AudioData, self.callback_audio_stream)
        rospy.Subscriber('/is_speeching', Bool, self.user_speaking)
        self.cout_speaking= 0
        self.max_no_voice = 1
        self.user_is_speaking = False
        # start the background thread 
        self.start()


    def stop(self):
        with self.condition:
            self.condition.notifyAll()


    def run(self):
        """
        background thread which wait for wakeword and recognize 
        whatever being said after wakeword
        """
        while not rospy.is_shutdown():
            with self.condition:
                self.condition.wait()
            if rospy.is_shutdown():
                break
            transcript = self.recognize_kaldi(10, [], clear_queue=True)
            print(transcript)
            if transcript:
                self.pub_partial.publish(transcript)
                self.recognize_pub.publish(transcript)

    def user_speaking(self, speech):
        if (speech.data):
          self.user_is_speaking = True
        if(self.user_is_speaking):
            if (not speech.data) and (self.cout_is_speak < self.max_no_voice): #6 continuous no speaking
                self.cout_is_speak +=1
                print("once false")
            elif speech.data:
                self.cout_is_speak = 0 #restart counter if again a speech detected is seen
            else:
                print("user is speaking false")
                self.user_is_speaking = False
        self.user_speaks.data = self.user_is_speaking
        self.pub_is_speaking.publish(self.user_speaks)

    def callback_audio_stream(self, msg):
        indata = bytes(msg.data)
        try:
            self.aqueue.put_nowait(indata)

        except:
            pass

        # check for hotword if kaldi is not busy recognizing 
        if self.user_is_speaking and not self.is_kaldi_recognizing:
                self.pub_voice_audio.publish(msg.data) #publish speech audio data while recognising
                with self.condition:
                    self.condition.notifyAll()


    """
        ros speech recognize callback
    """
    def callback_recognize(self, req):
        print("options:", len(req.options), req.options)
        print("language:", req.language)
        print("timeout:", str(req.timeout))
        timeout = (req.timeout if (req.timeout != 0) else 15)
        language = (req.language if (req.language != '') else self.language)
        options = list(filter(None, req.options)) # remove the empty options 

        # check if we need to change the language model
        # print('current language: ' + self.language)
        if language != self.language:
            print('switching language to ' + language)
            # VOSK python API does not implement exception!
            # so we need to check the path by ourselves 

            if os.path.exists(self.model_path + language):
                self.model = vosk.Model(self.model_path + language)
                self.language = language
            else:
                rospy.loginfo('could not load language model for ' + language)
                return speech_recognizeResponse('')

        transcript = self.recognize_kaldi(timeout, options, True)
        return speech_recognizeResponse(transcript)



    def contains_options(self, options, transcript):
        if not transcript:
            return None
        for opt in options:
            opt = opt.strip()
            # do not split the transcript of an option contains more than a word such as 'blue color'
            phrase = transcript if (len(opt.split()) > 1) else transcript.split()
            if opt and opt in phrase:
                return opt
        return None


    def recognize_kaldi(self, timeout, options, clear_queue=False):
        self.is_kaldi_recognizing = True
        if clear_queue:
            # example : if audio rate is 16000 and respeaker buffersize is 512, then the last one second will be around 31 item in queue
            while self.aqueue.qsize() > int(self.audio_rate / 512 / 2):
                self.aqueue.get()

        if options:
            rec = vosk.KaldiRecognizer(self.model, self.audio_rate, json.dumps(options, ensure_ascii=False))
        else:
            rec = vosk.KaldiRecognizer(self.model, self.audio_rate)

        t_start = time.time()
        rec.SetWords(True)
        rec.SetPartialWords(True)
        transcript = ''
        while True:
            data = self.aqueue.get()

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
                 if (len(partial) > 0):
                     self.pub_partial.publish(partial)
                 word = self.contains_options(options, partial)
                 if word:
                     transcript = word
                     break
            # check the timeout
            if ((time.time() - t_start) > timeout) or (self.user_is_speaking == False):
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
    speech.stop()

