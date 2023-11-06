#!/bin/bash

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
