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

"""Datatypes used by our abstract TCAM interpreter.

Essentially, this module defines the abstract syntax of IR programs, as well as
the state of our abstract TCAM machines. This file focuses on defining the types
themselves; functions for manipulating them are defined in the main file.
"""

import dataclasses
import enum
from typing import Union
import bitstring

Data = bitstring.BitArray

# Datatype definitions. We represent datatypes using the dataclass decorator
# with the frozen=True option. This means that each datatype represents an
# immutable collection of named data. We use dataclasses because they allow
# us to define methods in addition to data; most notably the __post_init__
# method, is executed whenever a value of a dataclass is constructed.
# We use this method to enforce invariants.


# We're representing machine integers, so bitwidths are important. The SizedInt
# class lets us represent ints with a particular bitwidth.
@dataclasses.dataclass(frozen=True)
class SizedInt:
  """Represents an unsigned integer with a particular bitwidth."""

  value: int
  width: int  # Width in bits

  def __post_init__(self) -> None:
    """Ensure the value falls in the range [0, 2^width)."""
    assert self.width > 0
    object.__setattr__(self, "value", self.value % (2**self.width))

  def __add__(self, other) -> "SizedInt":
    if self.width != other.width:
      raise RuntimeError(
          "Cannot add %s and %s: different widths." % (self, other)
      )
    return SizedInt(self.value + other.value, self.width)

  def __sub__(self, other) -> "SizedInt":
    if self.width != other.width:
      raise RuntimeError(
          "Cannot add %s and %s: different widths." % (self, other)
      )
    return SizedInt(self.value - other.value, self.width)

  def __lshift__(self, other) -> "SizedInt":
    return SizedInt(self.value << other.value, self.width)

  def __rshift__(self, other) -> "SizedInt":
    return SizedInt(self.value >> other.value, self.width)


# We begin by defining our two kinds of expressions:
# int-valued expressions and location expressions


class ArithOp(enum.Enum):
  """The types of arithmetic operations we support."""

  PLUS = "Plus"
  MINUS = "Minus"
  LSHIFT = "LShift"
  RSHIFT = "RShift"
  CAST = "Cast"


@dataclasses.dataclass(frozen=True)
class ArithExp:
  """An arithmetic expression. Should only appear inside an IntExp."""

  # If the operation is a unary cast, then left is the number of bits to cast
  # right to. This is slightly abusive -- the value of a cast is static, and
  # thus rightly isn't a proper IntExp -- but it simplifes the abstract syntax
  # significantly.
  op: ArithOp
  left: "IntExp"
  right: "IntExp"


@dataclasses.dataclass(frozen=True)
class IntExp:
  """Represents an int-valued expression.

  Possible expressions are:
  - A constant integer
  - A location
  - An arithmetic operation between two integer expressions
  """

  exp: Union[SizedInt, "LocationExp", ArithExp]

  def __post_init__(self) -> None:
    # Typechecker doesn't seem to catch this issue
    assert (
        isinstance(self.exp, SizedInt)
        or isinstance(self.exp, LocationExp)
        or isinstance(self.exp, ArithExp)
    )


@dataclasses.dataclass(frozen=True)
class Location:
  """A location refers to a range of bits in the packet or a data store."""

  name: str  # Name of the store/packet the range is referring to
  start: int  # First bit of the location (inclusive)
  end: int  # Last bit of the location (exclusive)
  length: int = dataclasses.field(init=False)  # Automatically computed below

  def __post_init__(self) -> None:
    assert 0 <= self.start <= self.end
    object.__setattr__(self, "length", self.end - self.start + 1)


@dataclasses.dataclass(frozen=True)
class LocationExp:
  """An expression that evaluates to a location.

  Unlike the Location type above, the start and end values may be expressions
  that have to be evaluated.
  """

  name: str  # Name of the store/packet the range is referring to
  start: IntExp  # First bit of the location (inclusive)
  end: IntExp  # Last bit of the location (exclusive)


@dataclasses.dataclass(frozen=True)
class DataStore:
  """DataStores generalize registers, storing a mutable array of bits.

  In addition to its stored value, each DataStore has several attributes:
  - read/write: indicate if the DataStore can be read/written, respectively
  - persistent: If True, the data store's value is visible after parsing.
  - masked_writes: If false, then writing to a subset of the data store's bits
    will set the unwritten bits to 0. Otherwise, the unwritten bits are
    unchanged.
  """

  value: Data
  read: bool
  write: bool
  persistent: bool
  masked_writes: bool


# Mutable since we don't pass the frozen=True flag. This allows us to modify
# it easily during interpretation.
@dataclasses.dataclass
class MachineState:
  """Represents the state of our abstract machine.

  Our machine has the following components:
  - cursor: indicates the first bit of the packet that has not yet been consumed
  - stage: indicates the next TCAM table to match against
  - stores: the set of data stores in the machine
  - keys: the locations which are matched against TCAM rules
  - headers: the set of extracted headers so far
  """

  cursor: int
  stage: int
  stores: dict[str, DataStore]
  keys: list[Location]
  headers: dict[str, Data]


class ActionType(enum.Enum):
  """The basic action types. Used to implement a tagged union."""

  MOVECURSOR = "MoveCursor"
  COPYDATA = "CopyData"
  EXTRACTHEADER = "ExtractHeader"


@dataclasses.dataclass(frozen=True)
class Action:
  """Represents one of the three generic TCAM actions and its arguments.

  Possible actions are:
  MoveCursor <intexp>
  CopyValue <intexp> <locexp>
  ExtractHeader <string> <locexp>
  """

  action_type: ActionType
  action_args: Union[
      IntExp | tuple[IntExp, LocationExp] | tuple[str, LocationExp]
  ]

  def __post_init__(self) -> None:
    """Ensure that the tag matches the argument type."""

    if self.action_type == ActionType.MOVECURSOR:
      assert isinstance(self.action_args, IntExp)

    if self.action_type == ActionType.COPYDATA:
      # Sadly, `isinstance(self.action_args, tuple[IntExp, LocationExp])`
      # doesn't work
      assert isinstance(self.action_args, tuple)
      assert len(self.action_args) == 2
      assert isinstance(self.action_args[0], IntExp)
      assert isinstance(self.action_args[1], LocationExp)

    if self.action_type == ActionType.EXTRACTHEADER:
      assert isinstance(self.action_args, tuple)
      assert len(self.action_args) == 2
      assert isinstance(self.action_args[0], str)
      assert isinstance(self.action_args[1], LocationExp)


@dataclasses.dataclass(frozen=True)
class Pattern:
  """Represents a TCAM pattern."""

  value: Data
  mask: Data

  def __post_init__(self) -> None:
    assert self.value.length == self.mask.length


Rule = tuple[list[Pattern], set[Action]]

Table = list[Rule]

TCAM = list[Table]
