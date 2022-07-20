cmake_minimum_required(VERSION 3.0.2)
project(vosk_asr)

find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
  hri_msgs
  message_generation
  pal_interaction_msgs
)

add_service_files(
   FILES
   speech_recognize.srv
)

generate_messages(
   DEPENDENCIES
   std_msgs
)

catkin_package(
   CATKIN_DEPENDS rospy std_msgs message_runtime hri_msgs pal_interaction_msgs
)
#include_directories(
#  ${catkin_INCLUDE_DIRS}
#)

catkin_install_python(PROGRAMS src/vosk_recognizer.py
   DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

