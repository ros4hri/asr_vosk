# asr_vosk

This repository is a PAL wrapper of offline Speech Recognition model [Vosk](https://alphacephei.com/vosk/).

## Preparation

The vosk node relies on models which are distributed in separate packages,
collected in the [vosk_language_models](https://gitlab/interaction/vosk_language_models) repository.
The related debians follow the naming scheme `pal-alum-asr-vosk-language-model-<locale>-<model_size>`,
where `<locale>` is the locale selected and `<size>`.

## ROS API

### Parameters

All parameters are loaded in the lifecycle `configuration` transition.

- `audio_rate` (int, default: 16000): Device sampling rate.
- `locale` (string, default: "en_US"):
  The desired locale, using following format:
  the [ISO 639-1 language code](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes),
  followed by an hyphen,
  followed by the [ISO 3166-1 alpha-2 region code](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2).
- `model_size` (string, default: "small"): Model size [small, large].
- `supported_locales` (string array):
  List of locales supported and configurable in the `locale` parameter.
  It is computed at runtime from the list of installed models found.

### Topics

#### Subscribed

- `/audio/channel0` ([audio_common_msgs/AudioData](https://github.com/ros-drivers/audio_common/blob/ros2/audio_common_msgs/msg/AudioData.msg)):
  Microphone audio stream.
- `/audio/voice_detected` ([std_msgs/Bool](https://github.com/ros2/common_interfaces/blob/humble/std_msgs/msg/Bool.msg)):
  Microphone voice activation detection.
- `/tts/goal` ([pal_tts_msgs/TTS Goal](https://gitlab/apps/pal_tts2/-/blob/main/pal_tts_msgs/action/TTS.action)):
  Goal of the robot text-to-speech action request.
  This is an optional topic, used to avoid speech detection of the robot's own speech.
  It must be used in conjunction with `/tts/result`.
- `/tts/result` ([pal_tts_msgs/TTS Result](https://gitlab/apps/pal_tts2/-/blob/main/pal_tts_msgs/action/TTS.action)):
  Result of the robot text-to-speech action request.
  This is an optional topic, used to avoid speech detection of the robot's own speech.
  It must be used in conjunction with `/tts/goal`.

#### Published

- `/humans/voices/tracked` ([hri_msgs/IdsList](https://github.com/ros4hri/hri_msgs/blob/humble-devel/msg/IdsList.msg)):
  List of voices ids detected (currently always only "anonymous_speaker").
- `/humans/voices/anonymous_speaker/audio` ([audio_common_msgs/AudioData](https://github.com/ros-drivers/audio_common/blob/ros2/audio_common_msgs/msg/AudioData.msg)):
  Voice audio stream.
- `/humans/voices/anonymous_speaker/is_speaking` ([std_msgs/Bool](https://github.com/ros2/common_interfaces/blob/humble/std_msgs/msg/Bool.msg)):
  Voice speech detection.
- `/humans/voices/anonymous_speaker/speech` ([hri_msgs/LiveSpeech](https://github.com/ros4hri/hri_msgs/blob/humble-devel/msg/LiveSpeech.msg)):
  Speech recognized.
- `/diagnostics` ([diagnostic_msgs/DiagnosticArray](https://github.com/ros2/common_interfaces/blob/humble/diagnostic_msgs/msg/DiagnosticArray.msg))

## Launch

```bash
ros2 launch asr_vosk asr_vosk.launch.py
```

The `asr_vosk.launch.py` launch file accepts as arguments and configures the defined [parameters](#parameters).
It also automatically transitions the node to the active state.

## Example

To test thepackage using the system default microphone:

1. Install the `audio_capture` package:
   `sudo apt install pal-alum-audio-capture`
1. Launch the `audio_capture` package:
   `ros2 launch audio_capture capture.launch.xml audio_topic:=channel0 format:=wave`
1. In a new terminal, launch the `asr_vosk` package:
   `ros2 launch asr_vosk asr_vosk.launch.py`
1. In a new terminal, manually activate the voice detection
   (`asr_vosk` will continuously attempt to recognize a speech, even no one is speaking):
   `ros2 topic pub --once /audio/voice_detected std_msgs/msg/Bool  "{data: true}"`
1. Check the recognized speech output:
   `ros2 topic echo /humans/voices/anonymous_speaker/speech`
