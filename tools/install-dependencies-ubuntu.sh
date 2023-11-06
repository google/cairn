#!/bin/bash

# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -e  # Exit on error
set -x  # Make command execution verbose

THIS_DIR=$( cd -- "$( dirname -- "${0}" )" &> /dev/null && pwd )
P4C_DIR=$(readlink -f ${THIS_DIR}/../p4c)

sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  bison \
  build-essential \
  ccache \
  cmake \
  curl \
  flex \
  g++ \
  git \
  libboost-dev \
  libboost-graph-dev \
  libboost-iostreams-dev \
  libfl-dev \
  libgc-dev \
  lld \
  pkg-config \
  python-is-python3 \
  python3 \
  python3-pip \
  python3-setuptools \
  tcpdump

sudo pip3 install --upgrade pip
sudo pip3 install -r ${P4C_DIR}/requirements.txt
