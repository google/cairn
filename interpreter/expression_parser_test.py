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

"""Test our ply-based expression parser."""

import unittest
import interpreter.datatypes as d
import interpreter.expression_parser as eparser


class ExpressionParserTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self.parser = eparser.Parser()

  def test_const_intexp(self):
    self.assertEqual(self.parser.parse("3"), d.IntExp(d.SizedInt(3, 32)))
    self.assertEqual(
        self.parser.parse("3w16"),
        d.IntExp(
            d.SizedInt(3, 16),
        ),
    )
    self.assertEqual(
        self.parser.parse("11399573w24"),
        d.IntExp(d.SizedInt(11399573, 24)),
    )
    self.assertEqual(  # Automatic wraparound if the bitsize is too small
        self.parser.parse("17w4"), d.IntExp(d.SizedInt(1, 4))
    )

    # Can't parse binary or hex ints this way.
    self.assertRaises(eparser.ParseError, self.parser.parse, "0b1101")
    self.assertRaises(eparser.ParseError, self.parser.parse, "0x1a5d")

  def test_locexp(self):
    self.assertEqual(  # Basic functionality
        self.parser.parse("packet[0:3]"),
        d.IntExp(
            d.LocationExp(
                "packet",
                d.IntExp(d.SizedInt(0, 32)),
                d.IntExp(d.SizedInt(3, 32)),
            )
        ),
    )
    self.assertEqual(  # The parser alone won't catch that the range is nonsense
        self.parser.parse("reg1[34:0]"),
        d.IntExp(
            d.LocationExp(
                "reg1",
                d.IntExp(d.SizedInt(34, 32)),
                d.IntExp(d.SizedInt(0, 32)),
            )
        ),
    )
    self.assertEqual(  # Technically allowed to specify widths, no point though
        self.parser.parse("foobar[0w4:3w16]"),
        d.IntExp(
            d.LocationExp(
                "foobar",
                d.IntExp(d.SizedInt(0, 4)),
                d.IntExp(d.SizedInt(3, 16)),
            )
        ),
    )

  def test_arithexp(self):
    # Test the basic operations
    self.assertEqual(
        self.parser.parse("3+ 4"),
        d.IntExp(
            d.ArithExp(
                d.ArithOp.PLUS,
                d.IntExp(d.SizedInt(3, 32)),
                d.IntExp(d.SizedInt(4, 32)),
            )
        ),
    )
    self.assertEqual(
        self.parser.parse("3 - 4"),
        d.IntExp(
            d.ArithExp(
                d.ArithOp.MINUS,
                d.IntExp(d.SizedInt(3, 32)),
                d.IntExp(d.SizedInt(4, 32)),
            )
        ),
    )
    self.assertEqual(
        self.parser.parse("3 <<4"),
        d.IntExp(
            d.ArithExp(
                d.ArithOp.LSHIFT,
                d.IntExp(d.SizedInt(3, 32)),
                d.IntExp(d.SizedInt(4, 32)),
            )
        ),
    )
    self.assertEqual(
        self.parser.parse("3>>4"),
        d.IntExp(
            d.ArithExp(
                d.ArithOp.RSHIFT,
                d.IntExp(d.SizedInt(3, 32)),
                d.IntExp(d.SizedInt(4, 32)),
            )
        ),
    )
    self.assertEqual(
        self.parser.parse("(w3)4w16"),
        d.IntExp(
            d.ArithExp(
                d.ArithOp.CAST,
                d.IntExp(d.SizedInt(3, 32)),
                d.IntExp(d.SizedInt(4, 16)),
            )
        ),
    )

    # No multiplication operator
    self.assertRaises(eparser.ParseError, self.parser.parse, "3*4")
    # No zero width casts
    self.assertRaises(eparser.ParseError, self.parser.parse, "(w0)3")

    # Test precedence
    self.assertEqual(
        self.parser.parse("3+(4>>5)"),
        d.IntExp(
            d.ArithExp(
                d.ArithOp.PLUS,
                d.IntExp(d.SizedInt(3, 32)),
                d.IntExp(
                    d.ArithExp(
                        d.ArithOp.RSHIFT,
                        d.IntExp(d.SizedInt(4, 32)),
                        d.IntExp(d.SizedInt(5, 32)),
                    )
                ),
            )
        ),
    )

    self.assertEqual(
        self.parser.parse("3+4>>5"),  # Equivalent to (3+4)>>5
        d.IntExp(
            d.ArithExp(
                d.ArithOp.RSHIFT,
                d.IntExp(
                    d.ArithExp(
                        d.ArithOp.PLUS,
                        d.IntExp(d.SizedInt(3, 32)),
                        d.IntExp(d.SizedInt(4, 32)),
                    )
                ),
                d.IntExp(d.SizedInt(5, 32)),
            ),
        ),
    )

    self.assertEqual(
        self.parser.parse("(w3)4>>5"),  # Equivalent to ((w3)4)>>5
        d.IntExp(
            d.ArithExp(
                d.ArithOp.RSHIFT,
                d.IntExp(
                    d.ArithExp(
                        d.ArithOp.CAST,
                        d.IntExp(d.SizedInt(3, 32)),
                        d.IntExp(d.SizedInt(4, 32)),
                    )
                ),
                d.IntExp(d.SizedInt(5, 32)),
            ),
        ),
    )

    self.assertEqual(
        self.parser.parse("3+4>>5<<6"),  # Equivalent to ((3+4)>>5)<<6)
        d.IntExp(
            d.ArithExp(
                d.ArithOp.LSHIFT,
                d.IntExp(
                    d.ArithExp(
                        d.ArithOp.RSHIFT,
                        d.IntExp(
                            d.ArithExp(
                                d.ArithOp.PLUS,
                                d.IntExp(d.SizedInt(3, 32)),
                                d.IntExp(d.SizedInt(4, 32)),
                            )
                        ),
                        d.IntExp(d.SizedInt(5, 32)),
                    )
                ),
                d.IntExp(d.SizedInt(6, 32)),
            ),
        ),
    )

  def test_nested_intexps(self):
    """More complicated tests after assuring ourselves that the basics work."""

    self.assertEqual(  # Arbitrary nesting of intexps is allowed
        self.parser.parse("packet[16+17:reg0[5:25]]"),
        d.IntExp(
            d.LocationExp(
                "packet",
                d.IntExp(
                    d.ArithExp(
                        d.ArithOp.PLUS,
                        d.IntExp(d.SizedInt(16, 32)),
                        d.IntExp(d.SizedInt(17, 32)),
                    )
                ),
                d.IntExp(
                    d.LocationExp(
                        "reg0",
                        d.IntExp(d.SizedInt(5, 32)),
                        d.IntExp(d.SizedInt(25, 32)),
                    )
                ),
            ),
        ),
    )

    self.assertEqual(  # Arbitrary nesting of intexps is allowed
        self.parser.parse("packet[reg1[5<<2:25+3>>6]:3+reg0[5:25]]"),
        d.IntExp(
            d.LocationExp(
                "packet",
                d.IntExp(
                    d.LocationExp(
                        "reg1",
                        d.IntExp(
                            d.ArithExp(
                                d.ArithOp.LSHIFT,
                                d.IntExp(d.SizedInt(5, 32)),
                                d.IntExp(d.SizedInt(2, 32)),
                            )
                        ),
                        d.IntExp(
                            d.ArithExp(
                                d.ArithOp.RSHIFT,
                                d.IntExp(
                                    d.ArithExp(
                                        d.ArithOp.PLUS,
                                        d.IntExp(d.SizedInt(25, 32)),
                                        d.IntExp(d.SizedInt(3, 32)),
                                    ),
                                ),
                                d.IntExp(d.SizedInt(6, 32)),
                            )
                        ),
                    )
                ),
                d.IntExp(
                    d.ArithExp(
                        d.ArithOp.PLUS,
                        d.IntExp(d.SizedInt(3, 32)),
                        d.IntExp(
                            d.LocationExp(
                                "reg0",
                                d.IntExp(d.SizedInt(5, 32)),
                                d.IntExp(d.SizedInt(25, 32)),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


if __name__ == "__main__":
  unittest.main()
