cmake_minimum_required(VERSION 3.0.2)
project(vosk_asr)

find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
  hri_msgs
  hri_actions_msgs
  message_generation
  pal_interaction_msgs
  catkin_virtualenv
)


catkin_package(
   CATKIN_DEPENDS rospy std_msgs message_runtime hri_msgs hri_actions_msgs pal_interaction_msgs
)

# Generate the virtualenv to install the vosk library
catkin_generate_virtualenv(
    INPUT_REQUIREMENTS requirements.in
    PYTHON_INTERPRETER python3
    CHECK_VENV ${CATKIN_ENABLE_TESTING} # workaround for https://github.com/locusrobotics/catkin_virtualenv/pull/89
    )

catkin_install_python(
    PROGRAMS
    src/vosk_recognizer.py
    src/vosk_tutorial.py
    DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

if (CMAKE_INSTALL_PREFIX MATCHES "install_pal_deploy/home/pal/deployed_ws$")
    message(NOTICE "Patching catkin virtualenv path for pal_deploy...")
    add_custom_target(${PROJECT_NAME}_fix_deploy ALL
      COMMAND ${CATKIN_ENV} rosrun catkin_virtualenv venv_relocate install/venv --target-dir /home/pal/deployed_ws/${CATKIN_PACKAGE_SHARE_DESTINATION}/venv
      COMMAND sed -i 's;${CMAKE_INSTALL_PREFIX}/;/home/pal/deployed_ws/;g' ${CMAKE_BINARY_DIR}/vosk_recognizer.py
      COMMAND sed -i 's;${CMAKE_INSTALL_PREFIX}/;/home/pal/deployed_ws/;g' ${CMAKE_BINARY_DIR}/vosk_tutorial.py
      DEPENDS ${PROJECT_NAME}_generate_virtualenv
    )
endif()

install(DIRECTORY config launch
    DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)

install(FILES requirements.txt
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION})
