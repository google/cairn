# Copyright 2023 Google LLC

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Higher-level tests for the interpreter.

In this file, we test the frontend's ability to read from files, and include
some end-to-end tests utilizing example files.
"""

import os
import unittest
from interpreter import interp
import interpreter.datatypes as d


def prefix_filename(filename: str) -> str:
  return os.path.join(
      "interpreter/test_files/",
      filename,
  )


# Helper functions to create dummy headers with the given field value.
# Other bits will be set to an arbitrary-but-fixed pattern to help identify
# which parts of the packet were read, which is helpful when debugging.
# Output is in hex format, using network byte order. Note that this is the same
# byte ordering used by patterns in the IR files.
def mk_eth(ethertype: str) -> str:
  src = "123456654321"
  dst = "abcdeffedcba"
  assert len(ethertype) == 4
  return src + dst + ethertype


def mk_ipv4(
    src: str = "12123434", ihl: str = "5", protocol: str = "99", rest: str = ""
) -> str:
  assert len(ihl) == 1
  assert len(protocol) == 2
  assert len(rest) == int(ihl, 16) * 8 - 40
  pre_src = "0" + ihl + "1122334455667788" + protocol + "aabb"
  dst = "ccddeeff"
  return pre_src + src + dst + rest


def mk_ipv6(
    src: str = "fedcba9876543210ffeeddccbbaa9988", next_header: str = "44"
) -> str:
  assert len(src) == 32
  assert len(next_header) == 2
  pre_src = "111122223333" + next_header + "44"
  dst = "55556666777788889999aaaabbbbcccc"
  return pre_src + src + dst


def mk_udp(dst_port: str = "9bdf") -> str:
  assert len(dst_port) == 4
  src_port = "1357"
  rest = "02468ace"
  return src_port + dst_port + rest


def mk_psp(next_header: str = "f0", hdr_ext_len: str = "e1") -> str:
  assert len(next_header) == 2
  assert len(hdr_ext_len) == 2
  rest = "d2c3b4a5968778"
  return next_header + hdr_ext_len + rest + rest


def mk_grt() -> str:
  return "0369" * 12


# Function that takes a concatenation of headers produced by the above
# functions and produces a packet value that can be manipulated by the
# interpreter. Note that this does not change the byte order.
def mk_packet(headers: str) -> d.Data:
  return d.Data("0x" + headers)


# Number of bits in each header
ETH_LEN = 112
IPV4_BASE_LEN = 160
IPV6_LEN = 320
UDP_LEN = 64
PSP_LEN = 128
GRT_LEN = 192
# Other important constants
ETHERTY_IPV4 = "0800"
ETHERTY_IPV6 = "86DD"
STATE_ACCEPT = "0x00000063"
STATE_REJECT = "0x00000064"


class EndToEndTest(unittest.TestCase):

  # Simple tests where we just make sure the functions work at all
  def test_frontend(self):
    interp.interp(
        prefix_filename("small_ir.json"),
        prefix_filename("sample_config.json"),
        "0xff00aaaa",
    )

    # Patterns and keys have different sizes
    self.assertRaises(
        RuntimeError,
        interp.interp,
        prefix_filename("small_ir_bin.json"),
        prefix_filename("sample_config.json"),
        "0xff00aaaa",
    )

  # Run some tests using the simple IP parser in our test files
  def test_simple_ip(self):
    ir_file = prefix_filename("simple_ip_parser.json")
    config_file = prefix_filename("simple_ip_config.json")

    bad_ipv4_address = "7f000001"
    good_ipv4_address = "76543210"
    some_ipv6_address = "fedcba9876543210ffeeddccbbaa9988"

    eth_hdr_ipv4 = mk_eth(ETHERTY_IPV4)
    eth_hdr_ipv6 = mk_eth(ETHERTY_IPV6)
    ipv4_hdr_good = mk_ipv4(good_ipv4_address)
    ipv4_hdr_bad = mk_ipv4(bad_ipv4_address)
    ipv6_hdr = mk_ipv6(some_ipv6_address)

    ipv4_packet_accept = "0x" + eth_hdr_ipv4 + ipv4_hdr_good
    ipv4_packet_reject = "0x" + eth_hdr_ipv4 + ipv4_hdr_bad
    ipv6_packet = "0x" + eth_hdr_ipv6 + ipv6_hdr
    nonsense_packet = "0x" + ipv6_hdr + ipv4_hdr_good + eth_hdr_ipv4

    # Things that should be true for all runs in this test
    def basic_checks(state, cursor_len, ethertype):
      self.assertEqual(state.cursor, cursor_len)
      self.assertEqual(state.stage, 3)
      self.assertEqual(len(state.headers), 2)
      self.assertIn("hdr.ethernet", state.headers)
      self.assertEqual(
          state.headers["hdr.ethernet"], mk_packet(mk_eth(ethertype))
      )

    # Should go through the sequence of states 1, 2, 99
    state = interp.interp(ir_file, config_file, ipv4_packet_accept)
    basic_checks(state, ETH_LEN + IPV4_BASE_LEN, ETHERTY_IPV4)
    self.assertIn("hdr.ipv4", state.headers)
    self.assertEqual(state.headers["hdr.ipv4"], mk_packet(ipv4_hdr_good))
    self.assertEqual(state.stores["state"].value, d.Data(STATE_ACCEPT))

    # Should go through the sequence of states 1, 2, 100
    state = interp.interp(ir_file, config_file, ipv4_packet_reject)
    basic_checks(state, ETH_LEN + IPV4_BASE_LEN, ETHERTY_IPV4)
    self.assertIn("hdr.ipv4", state.headers)
    self.assertEqual(state.headers["hdr.ipv4"], mk_packet(ipv4_hdr_bad))
    self.assertEqual(state.stores["state"].value, d.Data(STATE_REJECT))

    # Should go through the sequence of states 1, 3, 99
    state = interp.interp(ir_file, config_file, ipv6_packet)
    basic_checks(state, ETH_LEN + IPV6_LEN, ETHERTY_IPV6)
    self.assertIn("hdr.ipv6", state.headers)
    self.assertEqual(state.headers["hdr.ipv6"], mk_packet(ipv6_hdr))
    self.assertEqual(state.stores["state"].value, d.Data(STATE_ACCEPT))

    # Should only hit state 1
    state = interp.interp(ir_file, config_file, nonsense_packet)
    self.assertEqual(state.cursor, ETH_LEN)
    self.assertEqual(state.stage, 3)
    self.assertEqual(len(state.headers), 1)
    self.assertIn("hdr.ethernet", state.headers)  # Value isn't really important
    # Make sure we end in state 1
    self.assertEqual(state.stores["state"].value, d.Data("0x00000001"))


if __name__ == "__main__":
  unittest.main()
