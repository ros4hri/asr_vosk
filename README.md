# Vosk speech recognition using ROS audio


This repository is a PAL wrapper of offline Speech Recognition model
[Vosk](https://alphacephei.com/vosk/). It is originally based and shares license of example
taken from QTRobot (pending license approval), with quite a few adjustments to
suit our robots in any case. 

(source code:
https://github.com/luxai-qtrobot/software/blob/master/apps/qt_vosk_app/src/qt_vosk_app_node.py#L144)


## Vosk configuration files

You can include or edit the Vosk configuration file stored in
`/opt/pal/gallium/share/vosk_asr/vosk_recognizer_config.yaml`. It should look like
[vosk_recognizer_config.yaml](https://gitlab/interaction/vosk_asr/-/blob/main/config/vosk_recognizer_config.yaml).

## ROS interfaces

The Vosk node provides the following ROS interfaces. It subscribes to the
processed channel 0 `/audio/channel0` input from the ReSpeaker microphone and looks
for the currently active language model.

For example, if the language is *en_GB*, it
searches in the following order, always prioritizing large models. Note that if
for instance *en_GB* does not exist, it will then check for *en_XXX*, such as
*en_US*. 

- `/opt/pal/gallium/share/vosk_language_models/en_GB/small/`
- `/opt/pal/gallium/share/vosk_language_models/en_GB/large/`
- `/opt/pal/gallium/share/vosk_language_models/en_US/small/`
- ...


If no language exists, it will select the default language that is installed on
the robot, which is the small *en_US* model.

You can change the current active language with the ROS action
`/asr/set_locale`.


Recognised text is published on `/humans/voices/anonymous_speaker/speech`. 



**ROS actions**

- `start_asr` ROS action: type `hri_actions_msgs/StartASR` : starts processing
audio captured through the ReSpeaker microphone with Kaldi in a given language

- `stop_asr` ROS action: type `hri_actions_msgs/StopASR`: stops processing audio
captured


**Subscribed topics**

- `/audio/channel0` ROS topic: type `audio_common_msgs/AudioData`: processed
  audio of channel 0 published by the ReSpeaker array. **Note: **pending to
  merge https://gitlab/ros-overlays/respeaker_ros/-/tree/multichannel


- `/is_speeching` ROS topic:  type `std_msgs/Bool`: boolean indicating whether
  user is speaking or not, coming from the ReSpeaker array


**Published topics**

- `/humans/voices/anonymous_speaker/speech` ROS topic: type
  `hri_msgs/LiveSpeech`: publishes the incremental and final text recognized


- `/humans/voices/anonymous_speaker/is_speaking` ROS topic: type
  ``std_msgs/Bool`: publishes a boolean indicating whether a person is speaking
  or not


-  `/humans/voices/anonymous_speaker/audio` ROS topic: type
   `audio_common_msgs/AudioData`: republishes the `/audio/channel0`` processed
   audio topic coming from the ReSpeaker array

**ROS parameters**

- `/vosk_asr/audio_rate` (default: 16000)
- `/vosk_asr/vosk_model_path` (default:`/opt/pal/gallium/share/vosk_language_models/`)
- `/vosk_asr/default_language` (default: `en_US`)
- `/vosk_asr/model_size` (default: look for available ones, starting with the
  largest available size

## Adding a new Vosk language

The robot comes by default with the English language model, that is installed in
`/opt/pal/gallium/share/vosk_language_models/`, in addition to other languages
that were requested when buying the robot.  Models come from  Vosk language
models <https://alphacephei.com/vosk/models>`_ and may be small or large models.


Imagine you want to add a Spanish language model. As you see in `Vosk language
models <https://alphacephei.com/vosk/models>`_ there are both small and large
models available. Generally a larger model will produce a more accurate results,
but it will also be heavier on the CPU to run.  In this exercise we will add the
small model.


Download the small spanish model in the
`/home/pal/.pal/Vosk/vosk_language_models/es_ES/small` directory:

 ```
  ssh pal@ari-0c

   cd /home/pal/.pal/

   mkdir Vosk

   cd Vosk

   mkdir vosk_language_models

   cd vosk_language_models

   mkdir es_ES

   cd es_ES

   wget https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip
```


Make sure to unzip and rename the model accordingly. In the same directory, as
it is a small model:


```
   unzip vosk-model-small-es-0.42.zip
   mv vosk-model-small-es-0.42/ small/
```


The `vosk_asr` node will automatically be able to find this new model already
once it is restarted:

`rosrun pal_docker_vosk run_vosk.sh`


You are free to train new Vosk models in other languages as well, to do so
follow the **Training your own model** section of `Vosk tutorial
<https://alphacephei.com/vosk/models>`_. 


Check [vosk_language_models](https://gitlab/interaction/vosk_language_models)
and [pal_docker_vosk](https://gitlab/Dockers/pal_docker_vosk) README for more
details. 



## Testing ASR from the terminal

Once we have the desired language models, test it by calling the ROS action of `start_vosk`

```
   rostopic pub /start_asr/goal hri_action_msgs/StartASRActionGoal "header:
     seq: 0
     stamp:
       secs: 0
       nsecs: 0
     frame_id: ''
   goal_id:
     stamp:
       secs: 0
       nsecs: 0
     id: ''
   goal:
     language: 'es_ES'" 
```


Try to speak to the robot in spanish and monitor the recognized output:

```
   rostopic echo /humans/voices/anonymous_speaker/speech 
	header: 
	  seq: 1
	  stamp: 
	    secs: 0
	    nsecs:         0
	  frame_id: ''
	incremental: ''
	final: "hola encantada de conocerte"
	confidence: 0.0
```


Stop the recognizer:

```
	rostopic pub /stop_asr/goal hri_actions_msgs/StopASRActionGoal "header:
	  seq: 0
	  stamp:
	    secs: 0
	    nsecs: 0
	  frame_id: ''
	goal_id:
	  stamp:
	    secs: 0
	    nsecs: 0
	  id: ''
	goal: {}" 
```


Check to make sure the robot is no longer listening. You should get any output at all even if you speak 
to the robot.


`   rostopic echo /humans/voices/anonymous_speaker/speech `
   
    
Start Vosk again with a different language and repeat the procedure:
 
```
   rostopic pub /start_vosk/goal hri_actions_msgs/StartASRActionGoal "header:
     seq: 0
     stamp:
       secs: 0
       nsecs: 0
     frame_id: ''
   goal_id:
     stamp:
       secs: 0
       nsecs: 0
     id: ''
   goal:
     language: 'en_US'" 
```

## Testing ASR from code

From Python you can call the respective ROS actions, and subscribe to the audio transcription. In the 
example below, based on the speech it understands the robot will say something different using its
text-to-speech, calling the `/tts` action.

There is an example script in `vosk_asr/src/vosk_tutorial.py`


# Related repositories

[vosk_asr](https://gitlab/interaction/vosk_asr)

[vosk_language_models](https://gitlab/interaction/vosk_language_models)

[pal_docker_vosk](https://gitlab/Dockers/pal_docker_vosk)
