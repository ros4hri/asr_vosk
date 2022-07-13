# Vosk speech recognition using ROS audio

## Requirements 
- *Python 3*
- *vosk* and *vosk language models* for speech recogntion 

Note it is an example taken from QTRobot (pending license approval), with quite a few adjustments to suit our robots in any case. 

(source code: https://github.com/luxai-qtrobot/software/blob/master/apps/qt_vosk_app/src/qt_vosk_app_node.py#L144)


## Installation 

First pull the existing docker, that has RASA and Vosk installed and other needed dependencies:


`docker pull gitlab:4567/interaction/rasa_bots`

`docker run --device /dev/snd:/dev/snd --net=host -v /home/pal/voicebot_ws/:/home/user/ws/ -it gitlab:4567/interaction/rasa_bots:latest`


### Build the messages 
Copy the existing repository under /home/pal/voicebot_ws/src/ and build the workspace.

```
$ cd /home/user/ws/
$ source devel/setup.bash
$ catkin build vosk_asr
$ source devel/setup.bash

```

### Download the language models

Download desired Vosk language models from here https://alphacephei.com/vosk/models and copy them in the following directory inside the robot:

/home/voicebot_ws/src/ros-vosk/model/


Then rename the model folder in ISO language format name (e.g. en_GB, fr_FR)


## Lunching Vosk App service and trying it
```
$ roslaunch vosk_asr vosk_recognizer.launch 

```

open another terminal and try:
```
$ rosservice call /speech/recognize "language: 'en_US'
options:[]
timeout: 0"
```

or give your expected words as options. The app will look into the recognized script to find one of the option and return it. For example, for the following call, if you say *"Oh yes!"*, the resturn value of the service is *"yes"*.

```
$ rosservice call /speech/recognize "language: 'en_US'
options:['yes' 'no' 'maybe']
timeout: 0"
```

Note for PAL this is under testing

Instead of using the ROS service, the node also subscribes to respeaker_ros topics to start listening.

Once /is_speeching returns True, indicating a user is speaking, it will start publishing the following topics:

/humans/voices/anonymous_id/is_speaking [Bool] -> is a user speaking or not, remapping /is_speech from ReSpeaker

/humans/voices/anonymous_id/audio [AudioData] -> remaps /audio topic (channel 0 preprocessed audio from the mic) only when user is speaking


/humans/voices/anonymous_id/speech [String] -> partial words recognised, as long at least one word is recognized

/humans/voices/anonymous_id/speech_final [String] -> final sentence recognised, returned when user is detected not speaking after a while


## Data and testing

In the "data" folder there is already 2 rosbags with example input data, and also a vosk_recognizer.bag with example output. 
