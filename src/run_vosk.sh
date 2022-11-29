#! /bin/bash

DOCKER_IMAGE=gitlab:4567/dockers/pal_docker_vosk:latest
CONTAINER_NAME=pal_docker_vosk

#docker pull $DOCKER_IMAGE
docker stop $CONTAINER_NAME

docker system prune -f

#docker run --device /dev/snd:/dev/snd -v /etc/resolv.conf:/etc/resolv.conf  -v /home/pal/.pal/Vosk/:/home/ros/.pal/Vosk -v /opt/pal/gallium/share/vosk_language_models/:/opt/pal/gallium/share/vosk_language_models --name $CONTAINER_NAME --net=host --env ROS_MASTER_URI --privileged --entrypoint="/home/ros/start_vosk.sh" $DOCKER_IMAGE

docker run --device /dev/snd:/dev/snd -v /etc/resolv.conf:/etc/resolv.conf  -v /home/pal/.pal/Vosk/:/home/ros/.pal/Vosk -v /opt/pal/gallium/share/vosk_language_models/:/opt/pal/gallium/share/vosk_language_models --net=host --env ROS_MASTER_URI --privileged -it gitlab:4567/dockers/pal_docker_vosk:latest bash

