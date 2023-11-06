#!/bin/bash

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
