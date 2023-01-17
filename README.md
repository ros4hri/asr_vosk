# Vosk speech recognition using ROS audio


This repository is a PAL wrapper of offline Speech Recognition model [Vosk](https://alphacephei.com/vosk/). It is based and shares license of example taken from QTRobot (pending license approval), with quite a few adjustments to suit our robots in any case. 

(source code: https://github.com/luxai-qtrobot/software/blob/master/apps/qt_vosk_app/src/qt_vosk_app_node.py#L144)

At the moment this package is run from inside a docker image, see [pal_docker_vosk](https://gitlab/Dockers/pal_docker_vosk) for more details on how it is run. Reason: it is complicated to create a debian of the Vosk python library, see Dockerfile for related dependencies. 

This README will focus on the ROS interfaces in case it needs to be changed in the future.



## Vosk configuration files

You can include or edit the Vosk configuration file stored in
`/home/pal/.pal/Vosk/vosk_recognizer_config.yaml`. It should look like [vosk_recognizer_config.yaml](https://gitlab/interaction/vosk_asr/-/blob/main/config/vosk_recognizer_config.yaml). 
You can change the default language:

```
vosk_asr:
  audio_rate: 16000
  default_language: 'en_US' #option to change the default language
  vosk_model_path: '/home/ros/.pal/Vosk/vosk_language_models/'  
```
The language must exist, for instance, for English, in `/home/pal/.pal/Vosk/vosk_language_models/en`. 
This directory is mapped inside the Vosk docker when the main executable is run:

`rosrun pal_docker_vosk run_vosk.sh`

Specifically: 

`docker run --device /dev/snd:/dev/snd -v /etc/resolv.conf:/etc/resolv.conf  -v /home/pal/.pal/Vosk/:/home/ros/.pal/Vosk -v /opt/pal/gallium/share/vosk_language_models/:/opt/pal/gallium/share/vosk_language_models --net=host --env ROS_MASTER_URI --privileged -it gitlab:4567/dockers/pal_docker_vosk:latest bash`


## ROS interfaces

The Vosk node provides the following ROS interfaces. It subscribes to the processed channel 0
`/audio/channel0` input from the ReSpeaker microphone and, when the `start_asr` ROS action is called with the 
indicating language, it looks for the respective language model. For example, if the language is *en_GB*, it
searches in the following order, always prioritizing large models. Note that if for instance *en_GB* does not exist, it will then check for *en_XXX*, such as *en_US*. 

- `/home/pal/.pal/Vosk/vosk_language_models/en_GB/large/`

- `/home/pal/.pal/Vosk/vosk_language_models/en_GB/small/`

- `/home/pal/.pal/Vosk/vosk_language_models/en_US/large/`

- `/home/pal/.pal/Vosk/vosk_language_models/en_US/small/`

- `/opt/pal/gallium/share/vosk_language_models/en_GB/large/`

- `/opt/pal/gallium/share/vosk_language_models/en_GB/small/`

- `/opt/pal/gallium/share/vosk_language_models/en_US/large/`

- `/opt/pal/gallium/share/vosk_language_models/en_US/large/`

If no language exists, it will select the default language that is installed on the robot, which is the small
*en_US* model.

Once the language is selected, it will start processing the audio with Kaldi until the `stop_asr` ROS action
is called and published the recognized text in ``/humans/voices/anonymous_speaker/speech``. 



**ROS actions**

`start_asr` ROS action: type `hri_actions_msgs/StartASR` : starts processing audio captured through the ReSpeaker microphone with Kaldi in a given language

`stop_asr` ROS action: type `hri_actions_msgs/StopASR`: stops processing audio captured


**Subscribed topics**

`/audio/channel0` ROS topic: type `audio_common_msgs/AudioData`: processed audio of channel 0 published by the ReSpeaker array. **Note: **pending to merge https://gitlab/ros-overlays/respeaker_ros/-/tree/multichannel


`/is_speeching` ROS topic:  type `std_msgs/Bool`: boolean indicating whether user is speaking or not, 
coming from the ReSpeaker array


**Published topics**

`/humans/voices/anonymous_speaker/speech` ROS topic: type `hri_msgs/LiveSpeech`: publishes the incremental and final text recognized


`/humans/voices/anonymous_speaker/is_speaking` ROS topic: type ``std_msgs/Bool`: publishes a boolean indicating whether a person is speaking or not


`/humans/voices/anonymous_speaker/audio` ROS topic: type `audio_common_msgs/AudioData`: republishes the
`/audio/channel0`` processed audio topic coming from the ReSpeaker array




## Updating Vosk docker image


If any change is done to the `vosk_asr` package, you will need to rebuild the docker image. To do so, on your machine:

```
git clone git@gitlab:Dockers/pal_docker_vosk.git

cd ~/pal_docker_vosk

docker build gitlab:4567/dockers/pal_docker_vosk .

docker push gitlab:4567/dockers/pal_docker_vosk
```

This will have pushed the new image in the [container registry](https://gitlab/Dockers/pal_docker_vosk/container_registry). 
Restart the robot or re-run the main script that runs Vosk:

`rosrun pal_docker_vosk run_vosk.sh`


## Adding a new Vosk language

The robot comes by default with the English language model, that is installed in ``/opt/pal/gallium/share/vosk_language_models/``, in addition to other languages that were requested when buying the robot.
Models come from  `Vosk language models <https://alphacephei.com/vosk/models>`_ and may be small or large models.


Imagine you want to add a Spanish language model. As you see in `Vosk language models <https://alphacephei.com/vosk/models>`_ there are both small and large models available. Generally a larger model will produce a more 
accurate results, but it will also be heavier on the CPU to run.  In this exercise we will add the small model.


Download the small spanish model in the `/home/pal/.pal/Vosk/vosk_language_models/es_ES/small` directory:

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


Make sure to unzip and rename the model accordingly. In the same directory, as it is a small model:


```
   unzip vosk-model-small-es-0.42.zip
   mv vosk-model-small-es-0.42/ small/
```


The `vosk_asr` node will automatically be able to find this new model already once it is restarted:

`rosrun pal_docker_vosk run_vosk.sh`


You are free to train new Vosk models in other languages as well, to do so follow the **Training your own
model** section of `Vosk tutorial <https://alphacephei.com/vosk/models>`_. 


Check [vosk_language_models](https://gitlab/interaction/vosk_language_models) and [pal_docker_vosk](https://gitlab/Dockers/pal_docker_vosk) README for more details. 



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
