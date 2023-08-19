py_library(
    name = "datatypes",
    srcs = ["datatypes.py"],
    deps = [
	"@bitstring//:bitstring",
    ],
)

py_library(
    name = "expression_parser",
    srcs = ["expression_parser.py"],
    deps = [
        ":datatypes",
	"@ply//:ply",
    ],
)

py_test(
    name = "expression_parser_test",
    srcs = ["expression_parser_test.py"],
    deps = [
        ":datatypes",
        ":expression_parser",
    ],
)

py_library(
    name = "ir_parser",
    srcs = ["ir_parser.py"],
    deps = [
        ":datatypes",
        ":expression_parser",
    ],
)

py_test(
    name = "ir_parser_test",
    srcs = ["ir_parser_test.py"],
    deps = [
        ":datatypes",
        ":ir_parser",
    ],
)

py_library(
    name = "config_parser",
    srcs = ["config_parser.py"],
    deps = [
        ":datatypes",
        ":expression_parser",
    ],
)

py_test(
    name = "config_parser_test",
    srcs = ["config_parser_test.py"],
    deps = [
        ":config_parser",
        ":datatypes",
    ],
)

py_binary(
    name = "interp",
    srcs = ["interp.py"],
    deps = [
        ":config_parser",
        ":datatypes",
        ":ir_parser",
    ],
)

py_test(
    name = "interp_test",
    srcs = ["interp_test.py"],
    deps = [
        ":datatypes",
        ":interp",
    ],
)

py_test(
    name = "end_to_end_test",
    srcs = ["end_to_end_test.py"],
    data = [
        ":test_files/sample_config.json",
        ":test_files/simple_ip_config.json",
        ":test_files/simple_ip_parser.json",
        ":test_files/small_ir.json",
        ":test_files/small_ir_bin.json",
    ],
    deps = [
        ":datatypes",
        ":interp",
    ],
)
