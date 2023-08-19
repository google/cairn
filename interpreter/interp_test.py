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

"""Unit tests for interpreter."""

import unittest
from interpreter import interp
import interpreter.datatypes as d


# Dummy state to use during tests
def fresh_state():
  return d.MachineState(
      cursor=0,
      stage=0,
      stores={
          "r0": d.DataStore(d.Data("0x0000"), True, True, False, False),
          "r1": d.DataStore(d.Data("0x0000"), True, True, False, False),
          "r2": d.DataStore(d.Data("0x0000"), True, True, False, False),
          "flags": d.DataStore(d.Data("0x000faaaa"), True, True, False, True),
          "state": d.DataStore(d.Data("0x000f0000"), False, True, False, False),
          "metadata": d.DataStore(
              d.Data("0x0f0faaaa"), True, False, False, False
          ),
      },
      keys=[
          d.Location("r0", 0, 15),
          d.Location("r1", 0, 15),
          d.Location("state", 0, 23),
      ],
      headers={},
  )


packet = d.Data("0xF0F0F0F0FFFF0000AAAA")


# Helper function to create locations
def const_locexp(source, start, end):
  return d.LocationExp(
      source,
      d.IntExp(d.SizedInt(start, 32)),
      d.IntExp(d.SizedInt(end, 32)),
  )


class ExpTest(unittest.TestCase):
  """Test functionality related to arithmetic expressions and locations."""

  loc1 = const_locexp("flags", 0, 15)  # Should evaluate to 15

  loc2 = const_locexp("metadata", 0, 31)  # Should evaluate to 252684970

  loc3 = d.LocationExp(
      "state",
      d.IntExp(loc1),
      d.IntExp(d.SizedInt(15, 32)),
  )

  n8_32 = d.IntExp(d.SizedInt(8, 32))
  n16_32 = d.IntExp(d.SizedInt(16, 32))
  n3_4 = d.IntExp(d.SizedInt(3, 4))
  n12_4 = d.IntExp(d.SizedInt(12, 4))

  def test_locexp(self):
    """Test evaluating LocationExps to produce both Locations and SizedInts."""
    state = fresh_state()
    self.assertEqual(
        interp.evaluate_locexp(self.loc1, state, packet),
        d.Location("flags", 0, 15),
    )

    self.assertEqual(
        interp.evaluate_intexp(d.IntExp(self.loc1), state, packet),
        d.SizedInt(15, 16),
    )
    self.assertEqual(
        interp.evaluate_intexp(d.IntExp(self.loc2), state, packet),
        d.SizedInt(252684970, 32),
    )

    self.assertEqual(
        interp.evaluate_locexp(self.loc3, state, packet),
        d.Location("state", 15, 15),
    )

  def test_cast(self):
    """Test casting values."""
    state = fresh_state()

    cast1 = d.IntExp(d.ArithExp(d.ArithOp.CAST, self.n8_32, self.n16_32))
    self.assertEqual(
        interp.evaluate_intexp(cast1, state, packet), d.SizedInt(16, 8)
    )

    cast2 = d.IntExp(
        d.ArithExp(
            d.ArithOp.CAST,
            self.n8_32,
            d.IntExp(d.ArithExp(d.ArithOp.PLUS, self.n16_32, self.n8_32)),
        )
    )
    self.assertEqual(
        interp.evaluate_intexp(cast2, state, packet), d.SizedInt(24, 8)
    )

  def test_plus(self):
    """Test adding SizedInts."""
    state = fresh_state()

    plus1 = d.IntExp(d.ArithExp(d.ArithOp.PLUS, self.n8_32, self.n16_32))
    self.assertEqual(
        interp.evaluate_intexp(plus1, state, packet), d.SizedInt(24, 32)
    )

    plus2 = d.IntExp(d.ArithExp(d.ArithOp.PLUS, self.n3_4, self.n12_4))
    self.assertEqual(
        interp.evaluate_intexp(plus2, state, packet), d.SizedInt(15, 4)
    )

    plus3 = d.IntExp(d.ArithExp(d.ArithOp.PLUS, self.n3_4, plus2))
    self.assertEqual(
        interp.evaluate_intexp(plus3, state, packet), d.SizedInt(2, 4)
    )

    plus4 = d.IntExp(
        d.ArithExp(d.ArithOp.PLUS, self.n16_32, d.IntExp(self.loc2))
    )
    self.assertEqual(
        interp.evaluate_intexp(plus4, state, packet), d.SizedInt(252684986, 32)
    )

    mismatch1 = d.IntExp(d.ArithExp(d.ArithOp.PLUS, self.n16_32, self.n3_4))
    mismatch2 = d.IntExp(
        d.ArithExp(d.ArithOp.PLUS, self.n16_32, d.IntExp(self.loc3))
    )

    self.assertRaises(
        RuntimeError, interp.evaluate_intexp, mismatch1, state, packet
    )
    self.assertRaises(
        RuntimeError, interp.evaluate_intexp, mismatch2, state, packet
    )

  def test_minus(self):
    """Test subtracting SizedInts."""
    state = fresh_state()

    minus1 = d.IntExp(d.ArithExp(d.ArithOp.MINUS, self.n16_32, self.n8_32))
    self.assertEqual(
        interp.evaluate_intexp(minus1, state, packet), d.SizedInt(8, 32)
    )

    minus2 = d.IntExp(d.ArithExp(d.ArithOp.MINUS, self.n12_4, self.n3_4))
    self.assertEqual(
        interp.evaluate_intexp(minus2, state, packet), d.SizedInt(9, 4)
    )

    minus3 = d.IntExp(d.ArithExp(d.ArithOp.MINUS, self.n3_4, minus2))
    self.assertEqual(
        interp.evaluate_intexp(minus3, state, packet), d.SizedInt(3 - 9, 4)
    )

    mismatch1 = d.IntExp(d.ArithExp(d.ArithOp.MINUS, self.n16_32, self.n3_4))
    mismatch2 = d.IntExp(
        d.ArithExp(d.ArithOp.MINUS, self.n16_32, d.IntExp(self.loc3))
    )

    self.assertRaises(
        RuntimeError, interp.evaluate_intexp, mismatch1, state, packet
    )
    self.assertRaises(
        RuntimeError, interp.evaluate_intexp, mismatch2, state, packet
    )

  def test_shifts(self):
    """Test left and right shifts on SizedInts."""
    state = fresh_state()
    lshift1 = d.IntExp(d.ArithExp(d.ArithOp.LSHIFT, self.n16_32, self.n3_4))
    self.assertEqual(
        interp.evaluate_intexp(lshift1, state, packet), d.SizedInt(128, 32)
    )
    lshift2 = d.IntExp(d.ArithExp(d.ArithOp.LSHIFT, self.n3_4, self.n3_4))
    self.assertEqual(
        interp.evaluate_intexp(lshift2, state, packet), d.SizedInt(8, 4)
    )

    rshift1 = d.IntExp(d.ArithExp(d.ArithOp.RSHIFT, self.n16_32, self.n3_4))
    self.assertEqual(
        interp.evaluate_intexp(rshift1, state, packet), d.SizedInt(2, 32)
    )
    rshift2 = d.IntExp(d.ArithExp(d.ArithOp.RSHIFT, self.n12_4, self.n3_4))
    self.assertEqual(
        interp.evaluate_intexp(rshift2, state, packet), d.SizedInt(1, 4)
    )


# Helper functions to apply the basic action types


def move(pkt, state, n):
  interp.apply_action(
      d.Action(d.ActionType.MOVECURSOR, d.IntExp(d.SizedInt(n, 32))), state, pkt
  )


def extract(pkt, state, name, source, start, end):
  interp.apply_action(
      d.Action(
          d.ActionType.EXTRACTHEADER,
          (name, const_locexp(source, start, end)),
      ),
      state,
      pkt,
  )


def copy(pkt, state, intexp, loc):
  interp.apply_action(
      d.Action(
          d.ActionType.COPYDATA,
          (intexp, loc),
      ),
      state,
      pkt,
  )


class ActionTest(unittest.TestCase):
  """Test execution of each action type."""

  def test_move(self):
    state = fresh_state()
    move(packet, state, 4)
    self.assertEqual(state.cursor, 4)

    move(packet, state, 8)

    self.assertEqual(state.cursor, 12)

    self.assertRaises(RuntimeError, move, packet, state, 9999)

  def test_extract(self):
    state = fresh_state()
    extract(packet, state, name="h1", source="packet", start=0, end=0)

    self.assertEqual(state.headers["h1"], d.Data("0b1"))
    extract(packet, state, name="h2", source="packet", start=1, end=4)

    self.assertEqual(state.headers["h2"], d.Data("0b1110"))
    move(packet, state, 5)
    extract(packet, state, name="h3", source="packet", start=1, end=4)

    self.assertEqual(state.headers["h3"], d.Data("0b0011"))

    self.assertRaises(  # Extract from non-packet source
        RuntimeError,
        extract,
        packet,
        state,
        name="h4",
        source="r0",
        start=0,
        end=1,
    )

    self.assertRaises(  # Extract already-extracted header (h1)
        RuntimeError,
        extract,
        packet,
        state,
        name="h1",
        source="packet",
        start=0,
        end=1,
    )

  def test_copy(self):
    state = fresh_state()
    copy(
        packet,
        state,
        d.IntExp(const_locexp("packet", 0, 15)),
        const_locexp("r0", 0, 15),
    )

    copy(
        packet,
        state,
        d.IntExp(const_locexp("packet", 4, 19)),
        const_locexp("r1", 0, 15),
    )

    move(packet, state, 32)
    copy(
        packet,
        state,
        d.IntExp(const_locexp("packet", 8, 15)),
        const_locexp("r2", 0, 7),
    )

    self.assertEqual(state.stores["r0"].value, d.Data("0xF0F0"))
    self.assertEqual(state.stores["r1"].value, d.Data("0x0F0F"))
    self.assertEqual(state.stores["r2"].value, d.Data("0xFF00"))
    copy(
        packet,
        state,
        d.IntExp(const_locexp("r1", 8, 15)),
        const_locexp("state", 16, 23),
    )

    self.assertEqual(state.stores["state"].value, d.Data("0x00000F00"))

  def test_copy_bad(self):
    state = fresh_state()
    self.assertRaises(  # Size mismatch
        RuntimeError,
        copy,
        packet,
        state,
        d.IntExp(const_locexp("r0", 0, 15)),
        const_locexp("r1", 8, 15),
    )

    self.assertRaises(  # Can't read from state
        RuntimeError,
        copy,
        packet,
        state,
        d.IntExp(const_locexp("state", 0, 15)),
        const_locexp("r0", 0, 15),
    )

    self.assertRaises(  # Can't write to metadata
        RuntimeError,
        copy,
        packet,
        state,
        d.IntExp(const_locexp("r0", 0, 15)),
        const_locexp("metadata", 0, 15),
    )

    self.assertRaises(  # dst too small
        RuntimeError,
        copy,
        packet,
        state,
        d.IntExp(const_locexp("metadata", 0, 31)),
        const_locexp("r0", 0, 31),
    )

    self.assertRaises(  # Src too small
        RuntimeError,
        copy,
        packet,
        state,
        d.IntExp(const_locexp("r0", 0, 31)),
        const_locexp("state", 0, 31),
    )


# An arbitrary table for testing the interpreter. Can do more extensive tests
# once we have the parser working.
stage1: d.Table = [
    (  # First rule
        [  # Last bit of r0 is 1, penultimate bit of r1 is 0
            d.Pattern(d.Data("0xffff"), d.Data("0x0001")),
            d.Pattern(d.Data("0xff00"), d.Data("0x0002")),
            d.Pattern(d.Data("0xffffff"), d.Data("0x000000")),
        ],
        {
            d.Action(
                d.ActionType.EXTRACTHEADER,
                ("h1", const_locexp("packet", 4, 7)),
            ),
            d.Action(
                d.ActionType.EXTRACTHEADER,
                ("h2", const_locexp("packet", 8, 15)),
            ),
            d.Action(
                d.ActionType.COPYDATA,
                (
                    d.IntExp(const_locexp("packet", 8, 15)),
                    const_locexp("state", 8, 15),
                ),
            ),
            d.Action(d.ActionType.MOVECURSOR, d.IntExp(d.SizedInt(16, 32))),
        },
    ),
    (  # Second rule
        [  # Last bit of r0 is 0, penultimate bit of r1 is 1
            d.Pattern(d.Data("0xfff0"), d.Data("0x0001")),
            d.Pattern(d.Data("0xff02"), d.Data("0x0002")),
            d.Pattern(d.Data("0xffffff"), d.Data("0x000000")),
        ],
        {
            d.Action(
                d.ActionType.EXTRACTHEADER,
                ("h1", const_locexp("packet", 0, 3)),
            ),
            d.Action(d.ActionType.MOVECURSOR, d.IntExp(d.SizedInt(4, 32))),
            d.Action(
                d.ActionType.COPYDATA,
                (
                    d.IntExp(const_locexp("packet", 0, 3)),
                    const_locexp("flags", 0, 3),
                ),
            ),
        },
    ),
]


class InterpTest(unittest.TestCase):

  def test_step(self):
    """Test matching against the dummy table defined above."""

    state = fresh_state()
    state.stores["r0"].value[:] = 1
    # Should match the first rule
    interp.interp_step([stage1], state, packet)
    self.assertEqual(state.headers["h1"], d.Data("0x0"))
    self.assertEqual(state.headers["h2"], d.Data("0xf0"))
    self.assertEqual(state.stores["state"].value, d.Data("0x00f00000"))
    self.assertEqual(state.cursor, 16)

    state = fresh_state()
    state.stores["r1"].value[:] = 2
    # Should match the second rule
    interp.interp_step([stage1], state, packet)
    self.assertEqual(state.headers["h1"], d.Data("0xf"))
    self.assertNotIn("h2", state.headers)
    self.assertEqual(state.stores["flags"].value, d.Data("0xf00faaaa"))
    self.assertEqual(state.cursor, 4)

    state = fresh_state()
    # Should match neither rule
    interp.interp_step([stage1], state, packet)
    self.assertEqual(len(state.headers), 0)
    self.assertEqual(state.stores["state"].value, d.Data("0x000f0000"))
    self.assertEqual(state.stores["flags"].value, d.Data("0x000faaaa"))
    self.assertEqual(state.cursor, 0)


if __name__ == "__main__":
  unittest.main()
