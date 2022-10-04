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

/home/Vosk/models/


Then rename the model folder in ISO language format name (e.g. en_GB, fr_FR)


## Launching Vosk App service and trying it
```
$ roslaunch vosk_asr vosk_recognizer.launch 

```

To change the language:

```
$rosservice call /vosk_asr/set_lang "language: 'es_ES'" 
```


More advanced:

open another terminal and try:
```
$ rosservice call /speech/recognize "language: 'en_US'
options:[]
timeout: 0"
```

or give your expected words as options. The app will look into the recognized script to find one of the option and return it. For example, for the following call, if you say *"Oh yes!"*, the return value of the service is *"yes"*.

```
$ rosservice call /speech/recognize "language: 'en_US'
options:['yes' 'no' 'maybe']
timeout: 0"
```

Note for PAL recognising specific keywords like in the above example is under testing and right now the "options" parameter is ignored. 

Instead of using the ROS service, the node also subscribes to respeaker_ros topics to start listening.

Once /is_speeching returns True, indicating a user is speaking, it will start publishing the following topics:

`/humans/voices/anonymous_speaker/is_speaking` [`std_msgs/Bool`] -> is a user speaking or not, remapping /is_speech from ReSpeaker

`/humans/voices/anonymous_speaker/audio` [`sensor_msgs/AudioData`] -> the audio stream corresponding to this voice. In the current implementation (eg with no voice separation), simply republish the `/audio` topic (reSpeaker's `channel 0`  preprocessed audio) when voice activity is detected.


`/humans/voices/anonymous_speaker/speech` [`hri_msgs/LiveSpeech`]` -> incremental or final sentence recognised, as long at least one word is recognized



## Data and testing

In the "data" folder there are several rosbags with example input AudioData coming from the ReSpeaker that can be used for testing
