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
CAIRN_DIR=$(readlink -f ${THIS_DIR}/..)
P4C_DIR=$(readlink -f ${CAIRN_DIR}/p4c)

CMAKE_FLAGS=""

# Disable most backends
CMAKE_FLAGS+="-DENABLE_BMV2=OFF "
CMAKE_FLAGS+="-DENABLE_EBPF=OFF "
CMAKE_FLAGS+="-DENABLE_UBPF=OFF "
CMAKE_FLAGS+="-DENABLE_DPDK=OFF "
CMAKE_FLAGS+="-DENABLE_P4TC=OFF "

# Keep some useful backends for debugging
CMAKE_FLAGS+="-DENABLE_P4TEST=ON "
CMAKE_FLAGS+="-DENABLE_P4C_GRAPHS=ON "

# Link CAIRN compiler backend into p4c extensions directory
mkdir -p ${P4C_DIR}/extensions
ln -s -f ${CAIRN_DIR}/compiler ${P4C_DIR}/extensions/cairn

# Build and install
mkdir -p ${P4C_DIR}/build
cd ${P4C_DIR}/build
cmake ${CMAKE_FLAGS} ..
make
sudo make install
