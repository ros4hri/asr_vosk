#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import rospy

# Import required messages
from hri_msgs.msg import LiveSpeech
from actionlib import SimpleActionClient
from pal_interaction_msgs.msg import TtsAction, TtsGoal

# The following demo subscribes to speech-to-text output and triggers TTS
# based on response


class ASRDemo(object):
    def __init__(self):
        self.asr_sub = rospy.Subscriber(
            "/humans/voices/anonymous_speaker/speech", LiveSpeech, self.asr_result
        )
        self.tts_client = SimpleActionClient("/tts", TtsAction)
        self.language = "en_US"
        self.tts_client.wait_for_server()
        rospy.loginfo("ASR demo ready")

    def asr_result(self, msg):
        # Read speech to text output and trigger different actions accordingly
        sentence = msg.final
        rospy.loginfo("Understood sentence: " + sentence)
        if sentence == "what is your name?":
            self.tts_output("My name is ARI")
        elif sentence == "how are you?":
            self.tts_output("I am feeling great?")
        elif sentence == "goodbye":
            self.tts_output("See you!")

    def tts_output(self, answer):
        # Publishes TTS in given language
        self.tts_client.cancel_goal()
        goal = TtsGoal()
        goal.rawtext.lang_id = self.language
        goal.rawtext.text = str(answer)
        self.tts_client.send_goal_and_wait(goal)


if __name__ == "__main__":
    rospy.init_node("asr_demo")
    node = ASRDemo()
    rospy.spin()
