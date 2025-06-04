# Copyright (c) 2024 PAL Robotics S.L. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, RegisterEventHandler, Shutdown
from launch.events import matches_action
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_pal import get_pal_configuration
from launch_ros.actions import LifecycleNode
from launch_ros.events.lifecycle import ChangeState
from launch_ros.event_handlers import OnStateTransition
from lifecycle_msgs.msg import Transition


def generate_launch_description():
    use_vosk_venv_arg = DeclareLaunchArgument(
        'use_vosk_venv', default_value='True', description="Use the PAL Vosk virtual environment")
    use_vosk_venv = LaunchConfiguration('use_vosk_venv')

    pkg = 'asr_vosk'
    namespace = ''
    node_name = 'asr_vosk'
    node_executable = PythonExpression(
        ['"pal_asr_vosk" if ', use_vosk_venv, ' == True else "asr_vosk"'])

    ld = LaunchDescription()
    config = get_pal_configuration(pkg=pkg, node=node_name, ld=ld)

    node = LifecycleNode(
        package=pkg,
        executable=node_executable,
        namespace=namespace,
        name=node_name,
        parameters=config["parameters"],
        remappings=config["remappings"],
        arguments=config["arguments"],
        output='both',
        emulate_tty=True,
        on_exit=Shutdown()
    )

    configure_event = EmitEvent(event=ChangeState(
        lifecycle_node_matcher=matches_action(node),
        transition_id=Transition.TRANSITION_CONFIGURE))

    activate_event = RegisterEventHandler(OnStateTransition(
        target_lifecycle_node=node, goal_state='inactive',
        entities=[EmitEvent(event=ChangeState(
            lifecycle_node_matcher=matches_action(node),
            transition_id=Transition.TRANSITION_ACTIVATE))], handle_once=True))

    ld.add_action(use_vosk_venv_arg)
    ld.add_action(node)
    ld.add_action(configure_event)
    ld.add_action(activate_event)
    return ld
