load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

http_archive(
    name = "bitstring",
    url = "https://github.com/scott-griffiths/bitstring/archive/refs/tags/bitstring-4.1.0.tar.gz",
    build_file_content = """py_library(
      name = "bitstring",
      srcs = glob(["bitstring/*.py"]),
      visibility = ["//visibility:public"],
    )""",
)

http_archive(
    name = "ply",
    url = "https://github.com/dabeaz/ply/archive/refs/tags/3.11.tar.gz",
    build_file_content = """py_library(
      name = "ply",
      srcs = glob(["src/ply/*.py"]),
      visibility = ["//visibility:public"],
    )""",

)
