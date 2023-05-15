^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Changelog for package vosk_asr
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Forthcoming
-----------
* add CMake workaround to support pal_deploy with catkin-venv
* workaround https://github.com/locusrobotics/catkin_virtualenv/pull/89
* use catkin venv to add a dependency on vosk pip
* cleanly stop the node, even when no audio is published + avoid busy waits
* Contributors: Séverin Lemaignan

0.1.11 (2023-05-02)
-------------------
* publish final ASR result when speaker stops speaking
* Contributors: Séverin Lemaignan

0.1.10 (2023-04-14)
-------------------
* do not explicitely set the default language in launch file
  -> otherwise, impossible to set the value to a different default, eg for a specific customer
* Contributors: Séverin Lemaignan

0.1.9 (2023-04-14)
------------------
* publish /humans/voices/tracked + minor cleanup
* Contributors: Séverin Lemaignan

0.1.8 (2023-03-09)
------------------
* immediately start listening
  before, /start_asr/goal had to be called first
  While here, minor code improvmeent
* Contributors: Séverin Lemaignan

0.1.7 (2023-03-06)
------------------
* do not spam the console when no text is recognised
* Contributors: Séverin Lemaignan

0.1.6 (2023-03-06)
------------------
* {->audio}/voice_detected
* Contributors: Séverin Lemaignan

0.1.5 (2023-03-06)
------------------
* minor: code readability
* VAD now published on /voice_detected instead of /is_speeching
* Contributors: Séverin Lemaignan

0.1.4 (2023-01-24)
------------------
* refactor model loading
  - improved model size selection (added ROS param)
  - improved fallback mechanisms
  - use pathlib instead of os.path
* Contributors: Séverin Lemaignan

0.1.3 (2023-01-20)
------------------
* update path to default location for language models
* remove small en_US model from repo
  The model is available in package vosk-language-model-en-us-small
* [doc]
* Contributors: Séverin Lemaignan

0.1.2 (2023-01-17)
------------------
* fix some default path for the vosk docker image
* Contributors: Séverin Lemaignan

0.1.1 (2023-01-17)
------------------
* Start/StopASR actions are in hri_actions_msgs
* Contributors: Séverin Lemaignan

0.1.0 (2023-01-17)
------------------
* remove docker bash script
* Update README.md
* missing function and updating docker call
* channel input topic
* tutorial example, change ROS action type
* reset model path
* convert srvs to actions
* remove unused service
* Contributors: saracooper

0.0.2 (2022-11-17)
------------------
* 0.0.1
* install launch and configs
* Merge branch 'gallium' into 'main'
  Gallium
  See merge request interaction/vosk_asr!3
* check right directory of lang models
* example config of gallium lang models
* Merge branch 'multiple-languages' into 'main'
  Multiple languages
  See merge request interaction/vosk_asr!2
* add services to start and stop processing
* add options to switch language
* install config and launch files
* change model path
* Merge branch 'master' into 'main'
  ROS based vosk recognizer wrapper
  See merge request interaction/vosk_asr!1
* enable word by word publishing
* modify service names, typos
* not publish if tts running
* fix suggested changes
* Merge branch 'main' into 'master'
  # Conflicts:
  #   README.md
* add new rosbag data
* modify model paths
* ROS based vosk recognizer wrapper
* Initial commit
* Contributors: Sara Cooper, Séverin Lemaignan, saracooper
