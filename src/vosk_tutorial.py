#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import rospy
import time

# Import required messages
from hri_msgs.msg import LiveSpeech
from hri_actions_msgs.msg import (
    StartASRGoal,
    StartASRAction,
    StopASRGoal,
    StopASRAction,
)
from actionlib import SimpleActionClient
from pal_interaction_msgs.msg import TtsAction, TtsGoal
import actionlib
from std_msgs.msg import String

# The following demo subscribes to speech-to-text output and triggers TTS
# based on response


class ASRDemo(object):
    def __init__(self):
        self.asr_sub = rospy.Subscriber(
            "/humans/voices/anonymous_speaker/speech", LiveSpeech, self.asr_result
        )
        self.asr_start_action = SimpleActionClient("/start_asr", StartASRAction)
        self.asr_stop_action = SimpleActionClient("/stop_asr", StopASRAction)
        self.tts_client = SimpleActionClient("/tts", TtsAction)
        self.language = "en_US"
        self.asr_start_action.wait_for_server()
        self.asr_stop_action.wait_for_server()
        self.tts_client.wait_for_server()
        rospy.loginfo("ASR demo ready")
        self.start_listening()

    def start_listening(self):
        # Start processing audio with Vosk in en_GB language
        start_goal = StartASRGoal()
        start_goal.language = self.language
        self.asr_start_action.send_goal_and_wait(start_goal)

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
            # Stop listening
            stop_goal = StopVoskGoal()
            self.asr_stop_action.send_goal_and_wait(stop_goal)

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
