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

"""Tests for our configuration file parser."""

import unittest
from interpreter import config_parser
import interpreter.datatypes as d

example_store = {
    "name": "r1",
    "width": 24,
    "read": True,
    "write": True,
    "persistent": False,
    "masked-writes": False,
}


class ConfigParserTest(unittest.TestCase):

  def test_stores(self):
    self.assertEqual(
        config_parser.parse_data_store(example_store),
        (
            "r1",
            d.DataStore(
                value=d.Data("0x000000"),
                read=True,
                write=True,
                persistent=False,
                masked_writes=False,
            ),
        ),
    )

    # Make sure we get errors for missing/invalid field entries
    # name
    bad_store = dict(example_store)
    del bad_store["name"]
    self.assertRaises(
        config_parser.ParseError,
        config_parser.parse_data_store,
        dict(bad_store),
    )
    bad_store["name"] = 7
    self.assertRaises(
        config_parser.ParseError,
        config_parser.parse_data_store,
        dict(bad_store),
    )

    # width
    bad_store = dict(example_store)
    del bad_store["width"]
    self.assertRaises(
        config_parser.ParseError,
        config_parser.parse_data_store,
        dict(bad_store),
    )
    bad_store["width"] = "7"
    self.assertRaises(
        config_parser.ParseError,
        config_parser.parse_data_store,
        dict(bad_store),
    )

    # read
    bad_store = dict(example_store)
    del bad_store["read"]
    self.assertRaises(
        config_parser.ParseError,
        config_parser.parse_data_store,
        dict(bad_store),
    )
    bad_store["read"] = "7"
    self.assertRaises(
        config_parser.ParseError,
        config_parser.parse_data_store,
        dict(bad_store),
    )

    # write
    bad_store = dict(example_store)
    del bad_store["write"]
    self.assertRaises(
        config_parser.ParseError,
        config_parser.parse_data_store,
        dict(bad_store),
    )
    bad_store["write"] = "7"
    self.assertRaises(
        config_parser.ParseError,
        config_parser.parse_data_store,
        dict(bad_store),
    )

    # persistent
    bad_store = dict(example_store)
    del bad_store["persistent"]
    self.assertRaises(
        config_parser.ParseError,
        config_parser.parse_data_store,
        dict(bad_store),
    )
    bad_store["persistent"] = "7"
    self.assertRaises(
        config_parser.ParseError,
        config_parser.parse_data_store,
        dict(bad_store),
    )

    # masked-writes
    bad_store = dict(example_store)
    del bad_store["masked-writes"]
    self.assertRaises(
        config_parser.ParseError,
        config_parser.parse_data_store,
        dict(bad_store),
    )
    bad_store["masked-writes"] = "7"
    self.assertRaises(
        config_parser.ParseError,
        config_parser.parse_data_store,
        dict(bad_store),
    )

  def test_keys(self):
    self.assertEqual(
        config_parser.parse_keys({"keys": ["packet[0:15]"]}),
        [d.Location("packet", 0, 15)],
    )

    self.assertEqual(
        config_parser.parse_keys({"keys": ["r1[32:63]", "metadata[1:1]"]}),
        [d.Location("r1", 32, 63), d.Location("metadata", 1, 1)],
    )

    # No keys field
    self.assertRaises(
        config_parser.ParseError,
        config_parser.parse_keys,
        {},
    )

    # Empty key list
    self.assertRaises(
        config_parser.ParseError,
        config_parser.parse_keys,
        {"keys": []},
    )

    # Invalid key type
    self.assertRaises(
        config_parser.ParseError,
        config_parser.parse_keys,
        {"keys": [7]},
    )

    # Invalid key form
    self.assertRaises(
        config_parser.ParseError,
        config_parser.parse_keys,
        {"keys": ["7"]},
    )

    # Start must be less than end
    self.assertRaises(
        config_parser.ParseError,
        config_parser.parse_keys,
        {"keys": ["packet[44:15]"]},
    )

    # No nested expressions, just integers
    self.assertRaises(
        config_parser.ParseError,
        config_parser.parse_keys,
        {"keys": ["packet[44+4:150]"]},
    )

    # No nested expressions, just integers
    self.assertRaises(
        config_parser.ParseError,
        config_parser.parse_keys,
        {"keys": ["packet[44:r1[16:31]]"]},
    )


if __name__ == "__main__":
  unittest.main()
