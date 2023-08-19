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

"""Interpreter for the IR of our abstract TCAM state machine.

The goal of this interpter is to read an IR program written for the abstract
TCAM state machine, and simulate its behavior according to the state machine's
semantics.
"""

from typing import cast
from interpreter import config_parser
from interpreter import ir_parser
import interpreter.datatypes as d


def read_location(
    loc: d.Location, state: d.MachineState, packet: d.Data
) -> d.Data:
  """Read a designated range of bits from the packet or state."""
  if loc.name == "packet":
    if (state.cursor + loc.end + 1) > packet.length:
      raise RuntimeError(
          "Attempt to read %s in stage %s goes beyond end of packet. Current"
          " cursor value is %s, packet length is %s."
          % (loc, state.stage, state.cursor, packet.length)
      )
    src = cast(d.Data, packet[state.cursor :])
  else:
    store = state.stores[loc.name]
    if not store.read:
      raise RuntimeError(
          "Attempt to read %s failed: %s is not readable." % (loc, loc.name)
      )
    src = store.value

  if loc.length > src.length:
    raise RuntimeError(
        "Attempt to read %s failed: %s only has %s bits!"
        % (loc, loc.name, src.length)
    )

  # Cast to satisfy the type system; this will always return a d.Data
  return cast(d.Data, src[loc.start : loc.end + 1])


def evaluate_op(
    e: d.ArithExp, state: d.MachineState, packet: d.Data
) -> d.SizedInt:
  """Evaluate an arithmetic operation."""
  left = evaluate_intexp(e.left, state, packet)
  right = evaluate_intexp(e.right, state, packet)
  if e.op == d.ArithOp.CAST:
    return d.SizedInt(value=right.value, width=left.value)
  elif e.op == d.ArithOp.PLUS:
    # Note: this will wrap around on overflow.
    return left + right
  elif e.op == d.ArithOp.MINUS:
    # Note: this will wrap around on overflow.
    return left - right
  elif e.op == d.ArithOp.LSHIFT:
    return left << right
  else:
    assert e.op == d.ArithOp.RSHIFT
    return left >> right


def evaluate_locexp(
    locexp: d.LocationExp, state: d.MachineState, packet: d.Data
) -> d.Location:
  """Evaluate a location expression, returning a location value."""
  start = evaluate_intexp(locexp.start, state, packet).value
  end = evaluate_intexp(locexp.end, state, packet).value
  if start < 0:
    raise RuntimeError(
        "Location expression %s has negative start position %s! How did you do"
        " that?" % (locexp, start)
    )
  if start > end:
    raise RuntimeError(
        "Location expression %s has start position (%s) later than end"
        " position! (%s)!" % (locexp, start, end)
    )
  return d.Location(locexp.name, start, end)


def evaluate_intexp(
    intexp: d.IntExp, state: d.MachineState, packet: d.Data
) -> d.SizedInt:
  """Evaluate an d.IntExp in the current state, returning an int."""
  if isinstance(intexp.exp, d.SizedInt):
    return intexp.exp

  elif isinstance(intexp.exp, d.LocationExp):
    loc = evaluate_locexp(intexp.exp, state, packet)
    value = read_location(loc, state, packet).uint
    return d.SizedInt(value, loc.length)

  else:  # isinstance(intexp.exp, d.ArithExp)
    return evaluate_op(intexp.exp, state, packet)


def match_pattern(pat: d.Pattern, key: d.Data) -> bool:
  """Return true iff the pattern matches the key."""
  assert key.length == pat.value.length
  return key & pat.mask == pat.value & pat.mask


def apply_move(
    num_bits: d.IntExp, state: d.MachineState, packet: d.Data
) -> None:
  num_bits = evaluate_intexp(num_bits, state, packet)
  if (state.cursor + num_bits.value) > packet.length:
    raise RuntimeError(
        "Attempt to move cursor %s bits in stage %s goes beyond end of packet."
        " Current cursor value is %s, packet length is %s."
        % (num_bits.value, state.stage, state.cursor, packet.length)
    )
  state.cursor += num_bits.value


def apply_extract(
    name: str, loc: d.LocationExp, state: d.MachineState, packet: d.Data
) -> None:
  """Extract a header from the packet."""
  error_prefix = "Error while attempting to extract header %s: " % name
  if loc.name != "packet":
    raise RuntimeError(
        error_prefix + "extraction must always come from the packet."
    )
  if name in state.headers:
    raise RuntimeError(
        error_prefix + "a header with this name was already extracted."
    )
  loc = evaluate_locexp(loc, state, packet)
  state.headers[name] = read_location(loc, state, packet)


def apply_copy(
    value_exp: d.IntExp,
    dstloc: d.LocationExp,
    state: d.MachineState,
    packet: d.Data,
) -> None:
  """Copy data from the value from the destination location."""
  value = evaluate_intexp(value_exp, state, packet)
  value_as_data = d.Data(uint=value.value, length=value.width)
  dstloc = evaluate_locexp(dstloc, state, packet)

  error_prefix = "Error copying %s to %s: " % (value_exp, dstloc)

  # Make sure we're not writing to the packet, which is immutable.
  if dstloc.name == "packet":
    raise RuntimeError(error_prefix + "cannot write to packet.")

  # Ensure the destination location has the same length as the value
  if value_as_data.length != dstloc.length:
    raise RuntimeError(
        error_prefix
        + "value has length %s, while destination has length %s."
        % (value_as_data.length, dstloc.length)
    )

  # Get the appropriate data store, if it exists
  try:
    dst = state.stores[dstloc.name]
  except IndexError as e:
    raise RuntimeError(error_prefix + "no such destination store.") from e

  # Ensure destination is writeable
  if not dst.write:
    raise RuntimeError(error_prefix + "destination is not writeable.")
  # Check that the specified location actually fits in the store
  if dstloc.end >= dst.value.length:
    raise RuntimeError(
        error_prefix
        + "write ends at bit %s, but store %s only has %s bits!"
        % (dstloc.end, dstloc.name, dst.value.length)
    )

  if not dst.masked_writes:
    dst.value[:] = [0] * len(dst.value)
  dst.value[dstloc.start : dstloc.end + 1] = value_as_data


def apply_action(
    action: d.Action, state: d.MachineState, packet: d.Data
) -> None:
  """Modify the machine state by applying a single action."""
  if action.action_type == d.ActionType.MOVECURSOR:
    num_bits = cast(d.IntExp, action.action_args)
    apply_move(num_bits, state, packet)

  if action.action_type == d.ActionType.EXTRACTHEADER:
    name, loc = cast(tuple[str, d.LocationExp], action.action_args)
    apply_extract(name, loc, state, packet)

  if action.action_type == d.ActionType.COPYDATA:
    value_exp, dstloc = cast(tuple[d.IntExp, d.LocationExp], action.action_args)
    apply_copy(value_exp, dstloc, state, packet)


def table_match(table: d.Table, state: d.MachineState) -> set[d.Action]:
  """Perform a TCAM match using the current key values."""
  keys = [
      cast(d.Data, state.stores[loc.name].value[loc.start : loc.end + 1])
      for loc in state.keys
  ]
  # Note that we're matching rules left-to-right in the list, and we return
  # the first match we find.
  for rule in table:
    # Extract list of patterns, one pattern per key
    patterns = rule[0]
    # Match each pattern against the associated key
    match = [match_pattern(pat, keys[i]) for i, pat in enumerate(patterns)]
    # If all patterns match, the rule as a whole matches. Return its action set.
    if all(match):
      return rule[1]
  return set()


def interp_step(tcam: d.TCAM, state: d.MachineState, packet: d.Data) -> None:
  """Run the interpreter for one "step"; in this case, that means one TCAM stage."""
  if state.stage >= len(tcam):
    return
  table = tcam[state.stage]
  actions = table_match(table, state)
  # Make sure that we process move actions last, since they're the only ones
  # whose side effects affect other actions.
  move_actions = filter(
      lambda action: action.action_type == d.ActionType.MOVECURSOR, actions
  )
  other_actions = filter(
      lambda action: action.action_type != d.ActionType.MOVECURSOR, actions
  )
  for action in other_actions:
    apply_action(action, state, packet)
  for action in move_actions:
    apply_action(action, state, packet)
  state.stage += 1


def interp_tcam(tcam: d.TCAM, state: d.MachineState, packet: d.Data) -> None:
  while state.stage < len(tcam):
    interp_step(tcam, state, packet)


# Ensure that the keys specified in the machine state match the patterns of the
# TCAM. We assume the TCAM is well-formed, so all patterns have the same 'shape'
def validate_keys_patterns(tcam: d.TCAM, state: d.MachineState) -> None:
  first_patterns = tcam[0][0][0]  # Patterns of the first rule in the TCAM
  pattern_shapes = [p.value.length for p in first_patterns]
  if len(pattern_shapes) != len(state.keys):
    raise RuntimeError(
        "Key-pattern mismatch: Config file defines %s keys, but the tcam rules"
        " have %s patterns" % (len(state.keys), len(pattern_shapes))
    )
  for key, shape in zip(state.keys, pattern_shapes):
    if key.length != shape:
      raise RuntimeError(
          "Key-pattern mismatch: Key %s has length %s, but the corresponding"
          " pattern in the TCAM has length %s" % (key, key.length, shape)
      )


def interp(ir_file: str, config_file: str, packet_value: str) -> d.MachineState:
  """Parse commandline arguments and start the interpreter.

  Args:
    ir_file: path to a json file holding the ir program
    config_file: path to a json file holding the hardware configuration
    packet_value: binary or hex string representing an integer.

  Returns:
    The final machine state of the interpreter.
  """
  # Cast inexplicably necessary to satisfy type system
  packet = cast(d.Data, d.Data(packet_value))
  state = config_parser.parse(config_file, True)
  tcam = ir_parser.parse_ir(ir_file, True)
  validate_keys_patterns(tcam, state)
  interp_tcam(tcam, state, packet)
  return state
