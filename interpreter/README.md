# CAIRN: Constraint Aware IR for Networking – Interpreter
This folder contains the interpreter for CAIRN, as well as its tests. The interpreter is implemented in python 3, using the `bitstring` and `ply` libraries. It can be built using bazel. For a detailed description of the model and its capabilities, see the docs folder of this repo.


## Folder Structure
* `datatypes.py` defines the abstract syntax of the interpreter
* `interp.py` contains the actual interpretation code.
*  The various `_parser` files define parsers for IR files, configuration files, and our arithmetic expression language.
* The various `_test` files contain unit tests (and in one case, end-to-end tests) for the corresponding files. Tests can be run using e.g. `bazel test :end_to_end_tests`

## Using the Interpreter
The `test_files` directory contains a small number of simple example files demonstrating the expected form of IR and configuration files. For full details, consult the documentation.

To run the interpreter yourself, simply call the `interp` function in `interp.py` with the appropriate arguments; packets are expected to be passed as a bitstring starting with `0b` (for binary strings) or `0x` (for hexadecimal strings).
