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

from ament_index_python.packages import get_package_share_path
import subprocess


def test_in_venv():
    venv_python_path = str(get_package_share_path('asr_vosk') / 'venv' / 'bin' / 'python')
    cmd = [venv_python_path, '-m', 'pytest', '-s', 'test_in_venv']
    print(f'Executing venv testing subprocess: {cmd}')
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(process.stdout.decode("utf-8"))
    print(process.stderr.decode("utf-8"))
    assert process.returncode == 0
