# CAIRN: Constraint Aware IR for Networking

CAIRN (Constraint Aware IR for Networking) is a configurable abstract model of
packet processing hardware architecture, and an accompanying
[P4](https://p4.org/) compiler toolchain targeting this model.

## Status

This project is currently under active development, and not feature complete yet.

## Development guide

### Operating system

The following installation and building scripts have been tested on **Ubuntu 22.04**. If developing on other OSes, you are on your own to figure out these processes. The easiest way to set up a reproducible development environment is probably using a Docker container.

### Installation

Clone this repo and update all submodules:

```shell
git clone git@github.com:google/cairn.git
cd cairn
git submodule update --init --recursive
```

Install dependencies:

```shell
./tools/install-dependencies-ubuntu.sh
```

Build p4c with CAIRN backend:

```shell
./tools/build.sh
```

### Usage

At repo root, run:

```shell
mkdir -p scratch
p4c-cairn \
  -o scratch/test_out.p4 \
  --showIR \
  compiler/testdata/eth.p4
```

## Disclaimer

This is not an officially supported Google product.

## License

This software is distributed under the terms of the Apache License (Version
2.0).

See [LICENSE](LICENSE) for details.

The non-source code materials in this project are licensed under Creative
Commons - Attribution CC-BY 4.0,
https://creativecommons.org/licenses/by/4.0/legalcode.

See [LICENSE-docs](LICENSE-docs) for details.
