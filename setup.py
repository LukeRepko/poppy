#!/usr/bin/env python
# Copyright (c) 2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# THIS FILE IS MANAGED BY THE GLOBAL REQUIREMENTS REPO - DO NOT EDIT
import os

import setuptools


requirement_files = []
# walk the requirements directory and gather requirement files
for root, dirs, files in os.walk('requirements'):
    for requirements_file in files:
        requirements_file_path = os.path.join(root, requirements_file)
        requirement_files.append(requirements_file_path)

if 'requirements/requirements.txt' in requirement_files:
    requirement_files.remove('requirements/requirements.txt')

# parse all requirement files and generate requirements
requirements = []
for requirement_file in requirement_files:
    with open(requirement_file, "r") as f:
        for req in f.read().splitlines():
            if len(req) > 0 and not req.startswith('#'):
                requirements.append(req)

setuptools.setup(
    install_requires=requirements,
    setup_requires=['pbr==0.11.0', 'testrepository'],
    pbr=True)
