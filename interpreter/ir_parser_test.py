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

"""Tests for the IR Parser."""

import unittest
from interpreter import ir_parser
import interpreter.datatypes as d


class IrParserTest(unittest.TestCase):

  def test_pattern(self):
    # Simple tests, no stars
    self.assertEqual(
        ir_parser.parse_pattern("0b0010"),
        d.Pattern(d.Data("0b0010"), d.Data("0b1111")),
    )
    self.assertEqual(
        ir_parser.parse_pattern("0x0a9f"),
        d.Pattern(d.Data("0x0a9f"), d.Data("0xffff")),
    )

    # Simple tests with stars
    self.assertEqual(
        ir_parser.parse_pattern("0b0*1*"),
        d.Pattern(d.Data("0b0010"), d.Data("0b1010")),
    )
    self.assertEqual(
        ir_parser.parse_pattern("0x*a*f"),
        d.Pattern(d.Data("0x0a0f"), d.Data("0x0f0f")),
    )

    # Make sure all hex characters work
    self.assertEqual(
        ir_parser.parse_pattern("0x0123456789abcdef*"),
        d.Pattern(d.Data("0x0123456789abcdef0"), d.Data("0xffffffffffffffff0")),
    )

    # No prefix
    self.assertRaises(ir_parser.ParseError, ir_parser.parse_pattern, "101")
    # Bad prefix
    self.assertRaises(ir_parser.ParseError, ir_parser.parse_pattern, "0q101")
    # Wrong digits for prefix
    self.assertRaises(ir_parser.ParseError, ir_parser.parse_pattern, "0b0d3")
    self.assertRaises(ir_parser.ParseError, ir_parser.parse_pattern, "0xkjy")
    self.assertRaises(ir_parser.ParseError, ir_parser.parse_pattern, "0x#%&")

  def test_move(self):
    self.assertEqual(  # Basic test
        ir_parser.parse_action({"type": "MoveCursor", "numbits": "7"}),
        d.Action(d.ActionType.MOVECURSOR, d.IntExp(d.SizedInt(7, 32))),
    )

    self.assertEqual(  # Extraneous fields are silently ignored
        ir_parser.parse_action(
            {"type": "MoveCursor", "numbits": "7w16", "foo": 17, "loc": []}
        ),
        d.Action(d.ActionType.MOVECURSOR, d.IntExp(d.SizedInt(7, 16))),
    )

    self.assertEqual(  # Test other intexps
        ir_parser.parse_action(
            {"type": "MoveCursor", "numbits": "packet[13:22]"}
        ),
        d.Action(
            d.ActionType.MOVECURSOR,
            d.IntExp(
                d.LocationExp(
                    "packet",
                    d.IntExp(d.SizedInt(13, 32)),
                    d.IntExp(d.SizedInt(22, 32)),
                )
            ),
        ),
    )

    self.assertEqual(  # Test other intexps
        ir_parser.parse_action({"type": "MoveCursor", "numbits": "13w4+12w4"}),
        d.Action(
            d.ActionType.MOVECURSOR,
            d.IntExp(
                d.ArithExp(
                    d.ArithOp.PLUS,
                    d.IntExp(d.SizedInt(13, 4)),
                    d.IntExp(d.SizedInt(12, 4)),
                )
            ),
        ),
    )

    # No type field
    self.assertRaises(ir_parser.ParseError, ir_parser.parse_action, {})
    # Nonsense type field
    self.assertRaises(
        ir_parser.ParseError,
        ir_parser.parse_action,
        {"type": "MoveCahsah", "numbits": "2"},
    )
    # No numbits field
    self.assertRaises(
        ir_parser.ParseError,
        ir_parser.parse_action,
        {"type": "MoveCursor", "loc": []},
    )

  def test_extract(self):
    self.assertEqual(  # Basic test
        ir_parser.parse_action(
            {"type": "ExtractHeader", "id": "foo", "loc": "packet[0:12]"}
        ),
        d.Action(
            d.ActionType.EXTRACTHEADER,
            (
                "foo",
                d.LocationExp(
                    "packet",
                    d.IntExp(d.SizedInt(0, 32)),
                    d.IntExp(d.SizedInt(12, 32)),
                ),
            ),
        ),
    )

    self.assertEqual(  # Extraneous fields are silently ignored
        ir_parser.parse_action({
            "type": "ExtractHeader",
            "id": "foo",
            "loc": "packet[0:12]",
            "baz": [12],
        }),
        d.Action(
            d.ActionType.EXTRACTHEADER,
            (
                "foo",
                d.LocationExp(
                    "packet",
                    d.IntExp(d.SizedInt(0, 32)),
                    d.IntExp(d.SizedInt(12, 32)),
                ),
            ),
        ),
    )

    # No loc
    self.assertRaises(
        ir_parser.ParseError,
        ir_parser.parse_action,
        {
            "type": "ExtractHeader",
            "id": "foo",
        },
    )

    # No id
    self.assertRaises(
        ir_parser.ParseError,
        ir_parser.parse_action,
        {
            "type": "ExtractHeader",
            "loc": "packet[0:12]",
        },
    )

  def test_copy(self):
    self.assertEqual(  # Basic test
        ir_parser.parse_action(
            {"type": "CopyData", "src": "9w12", "dst": "reg0[0:12]"}
        ),
        d.Action(
            d.ActionType.COPYDATA,
            (
                d.IntExp(d.SizedInt(9, 12)),
                d.LocationExp(
                    "reg0",
                    d.IntExp(d.SizedInt(0, 32)),
                    d.IntExp(d.SizedInt(12, 32)),
                ),
            ),
        ),
    )

    self.assertEqual(  # Extraneous fields are silently ignored
        ir_parser.parse_action({
            "type": "CopyData",
            "src": "9w12",
            "dst": "reg0[0:12]",
            "numbits": 19,
        }),
        d.Action(
            d.ActionType.COPYDATA,
            (
                d.IntExp(d.SizedInt(9, 12)),
                d.LocationExp(
                    "reg0",
                    d.IntExp(d.SizedInt(0, 32)),
                    d.IntExp(d.SizedInt(12, 32)),
                ),
            ),
        ),
    )

    # No dst
    self.assertRaises(
        ir_parser.ParseError,
        ir_parser.parse_action,
        {
            "type": "CopyData",
            "src": "9w12",
        },
    )

    # No src
    self.assertRaises(
        ir_parser.ParseError,
        ir_parser.parse_action,
        {
            "type": "CopyData",
            "dst": "reg0[0:12]",
        },
    )

  def test_rule(self):
    self.assertEqual(
        ir_parser.parse_rule(
            0,
            0,
            {
                "table": 0,
                "rule": 0,
                "patterns": ["0b110*", "0x1*f8"],
                "actions": [
                    {
                        "type": "CopyData",
                        "src": "9w12",
                        "dst": "reg0[0:12]",
                    },
                    {"type": "MoveCursor", "numbits": "7"},
                ],
            },
        ),
        (
            [
                d.Pattern(d.Data("0b1100"), d.Data("0b1110")),
                d.Pattern(d.Data("0x10f8"), d.Data("0xf0ff")),
            ],
            {
                d.Action(d.ActionType.MOVECURSOR, d.IntExp(d.SizedInt(7, 32))),
                d.Action(
                    d.ActionType.COPYDATA,
                    (
                        d.IntExp(d.SizedInt(9, 12)),
                        d.LocationExp(
                            "reg0",
                            d.IntExp(d.SizedInt(0, 32)),
                            d.IntExp(d.SizedInt(12, 32)),
                        ),
                    ),
                ),
            },
        ),
    )

    # No action field
    self.assertRaises(
        ir_parser.ParseError,
        ir_parser.parse_rule,
        0,
        0,
        {
            "table": 0,
            "rule": 0,
            "patterns": ["0b110*", "0x1*f8"],
        },
    )

    # Invalid pattern
    self.assertRaises(
        ir_parser.ParseError,
        ir_parser.parse_rule,
        0,
        0,
        {
            "table": 0,
            "rule": 0,
            "patterns": ["17*", "0x1*f8"],
            "actions": [],
        },
    )

    # Ill-typed pattern field
    self.assertRaises(
        ir_parser.ParseError,
        ir_parser.parse_rule,
        0,
        0,
        {
            "table": 0,
            "rule": 0,
            "patterns": [12, "0x1*f8"],
            "actions": [],
        },
    )

    # No patterns field
    self.assertRaises(
        ir_parser.ParseError,
        ir_parser.parse_rule,
        0,
        0,
        {
            "table": 0,
            "rule": 0,
            "actions": [
                {
                    "type": "CopyData",
                    "src": "9w12",
                    "dst": "reg0[0:12]",
                },
                {"type": "MoveCursor", "numbits": "7"},
            ],
        },
    )

    # Invalid action
    self.assertRaises(
        ir_parser.ParseError,
        ir_parser.parse_rule,
        0,
        0,
        {
            "table": 0,
            "rule": 0,
            "patterns": [],
            "actions": [
                {
                    "type": "None",
                    "src": "9w12",
                    "dst": "reg0[0:12]",
                },
                {"type": "MoveCursor", "numbits": "7"},
            ],
        },
    )

    # Ill-typed action field
    self.assertRaises(
        ir_parser.ParseError,
        ir_parser.parse_rule,
        0,
        0,
        {
            "table": 0,
            "rule": 0,
            "patterns": [],
            "actions": {
                "type": "CopyData",
                "src": "9w12",
                "dst": "reg0[0:12]",
            },
        },
    )

    # No table field
    self.assertRaises(
        ir_parser.ParseError,
        ir_parser.parse_rule,
        0,
        0,
        {
            "rule": 0,
            "patterns": [12, "0x1*f8"],
            "actions": [],
        },
    )

    # No rule field
    self.assertRaises(
        ir_parser.ParseError,
        ir_parser.parse_rule,
        0,
        0,
        {
            "table": 0,
            "patterns": [12, "0x1*f8"],
            "actions": [],
        },
    )

    # Ill-typed table field
    self.assertRaises(
        ir_parser.ParseError,
        ir_parser.parse_rule,
        0,
        0,
        {
            "table": "0",
            "rule": 0,
            "patterns": [12, "0x1*f8"],
            "actions": [],
        },
    )

    # Ill-typed rule field
    self.assertRaises(
        ir_parser.ParseError,
        ir_parser.parse_rule,
        0,
        0,
        {
            "table": 0,
            "rule": "7",
            "patterns": [12, "0x1*f8"],
            "actions": [],
        },
    )

    # Incorrect table value
    self.assertRaises(
        ir_parser.ParseError,
        ir_parser.parse_rule,
        0,
        0,
        {
            "table": 1,
            "rule": 0,
            "patterns": [12, "0x1*f8"],
            "actions": [],
        },
    )

    # Incorrect rule value
    self.assertRaises(
        ir_parser.ParseError,
        ir_parser.parse_rule,
        0,
        0,
        {
            "table": 0,
            "rule": 1,
            "patterns": [12, "0x1*f8"],
            "actions": [],
        },
    )


if __name__ == "__main__":
  unittest.main()
