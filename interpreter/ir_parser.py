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

"""Parse IR files, represented as a json, to produce a TCAM datatype.

This file is only concerned with parsing the TCAM file. Most of the file is 
dedicated to validating the json; the parsing is relatively straightforward.
"""


from collections.abc import Mapping, Sequence
import json
import re
from typing import cast

import interpreter.datatypes as d
import interpreter.expression_parser as eparser

expression_parser = eparser.Parser()
ParseError = eparser.ParseError


# Regex definitions, defined at top-level to allow for re-use
# Characters allowed in the hex representation of an integer
hex_char_exp = re.compile(r"[0-9a-fA-F]")
# Either '0b' followed by a string of bits, some of which may be '*', or
# '0x' followed by a string of hex digits, some of which may be '*'
pattern_exp = re.compile(r"^(0b[01*]+|0x[0-9a-fA-F*]+)$")


# Check if an object is a sequence of strings, since
# isinstance(Sequence[string]) doesn't work
def is_stringlist(obj: object) -> bool:
  return isinstance(obj, Sequence) and all(
      [isinstance(elt, str) for elt in obj]
  )


# Check if an object is a dict of strings to strings, since
# isinstance(Mapping[string, string]) doesn't work
def is_strdict(obj: object) -> bool:
  return (
      isinstance(obj, Mapping)
      and is_stringlist(list(obj.keys()))
      and is_stringlist(list(obj.values()))
  )


def parse_pattern(pat: str) -> d.Pattern:
  """Parse a binary or hexadecimal pattern into a (mask, value) pair."""
  if not (re.match(pattern_exp, pat)):
    raise ParseError(
        "Error parsing pattern "
        + pat
        + ". Patterns should start with either '0b' for binary patterns, or "
        + "'0x' for hex patterns, and be followed by a string of appropriate "
        + "digits, some of which may be '*' instead."
    )
  # Convert patterns into proper binary/hex strings (no *)
  value = pat.replace("*", "0")  # Works for both binary and hex

  # Replace all non-* characters with 0, and * with the max digit
  if pat.startswith("0b"):
    # Don't replace in the prefix
    mask = pat[:2] + pat[2:].replace("0", "1").replace("*", "0")
  else:
    assert pat.startswith("0x")
    mask = pat[:2] + re.sub(hex_char_exp, "f", pat[2:]).replace("*", "0")
  # Cast is inexplicably necessary to satisfy the type system
  return d.Pattern(cast(d.Data, d.Data(value)), cast(d.Data, d.Data(mask)))


def parse_locexp(exp: str) -> d.LocationExp:
  parsed_exp = expression_parser.parse(exp)
  if not isinstance(parsed_exp.exp, d.LocationExp):
    raise ParseError("Unable to parse " + exp + " as a location expression.")
  return parsed_exp.exp


def parse_intexp(exp: str) -> d.IntExp:
  return expression_parser.parse(exp)


def parse_move(args: Mapping[str, str]) -> d.Action:
  if "numbits" not in args:
    raise ParseError(
        "Error parsing action %s: Move actions are expected to have 'numbits'"
        " field." % args
    )
  intexp = parse_intexp(args["numbits"])
  return d.Action(d.ActionType.MOVECURSOR, intexp)


def parse_copy(args: Mapping[str, str]) -> d.Action:
  if "src" not in args or "dst" not in args:
    raise ParseError(
        "Error parsing action %s: Copy actions are expected to have 'src' and"
        " 'dst' fields." % args
    )
  src = parse_intexp(args["src"])
  dst = parse_locexp(args["dst"])
  return d.Action(d.ActionType.COPYDATA, (src, dst))


def parse_extract(args: Mapping[str, str]) -> d.Action:
  if "id" not in args or "loc" not in args:
    raise ParseError(
        "Error parsing action %s: Extract actions are expected to have 'id' and"
        " 'loc' fields." % args
    )
  name = args["id"]
  loc = parse_locexp(args["loc"])
  return d.Action(d.ActionType.EXTRACTHEADER, (name, loc))


def parse_action(args: Mapping[str, str]) -> d.Action:
  """Check an action's type and call the appropriate parsing function."""
  error_prefix = "Error parsing action %s: " % args
  if "type" not in args:
    raise ParseError(
        error_prefix + "Actions are expected to have 'type' field."
    )
  if args["type"] == "MoveCursor":
    return parse_move(args)
  if args["type"] == "CopyData":
    return parse_copy(args)
  if args["type"] == "ExtractHeader":
    return parse_extract(args)

  raise ParseError(
      error_prefix
      + "Invalid action type. Expected 'MoveCursor', 'CopyData', or"
      " 'ExtractHeader'"
  )


def parse_rule(table_idx: int, rule_idx: int, rule: object) -> d.Rule:
  """Parse a single TCAM rule."""
  error_prefix = "Error parsing rule %s in table %s: " % (rule_idx, table_idx)
  if (
      not isinstance(rule, Mapping)
      or "patterns" not in rule
      or "actions" not in rule
      or "table" not in rule
      or "rule" not in rule
  ):
    raise ParseError(
        error_prefix
        + "Rules are expected to be json objects with 'patterns' and 'actions'"
        " fields, as well as 'table' and 'rule' fields."
    )
  rule = cast(Mapping[str, object], rule)

  # Ensure rule and table annotations match the position in the file
  table_annot = rule["table"]
  rule_annot = rule["rule"]
  if not isinstance(table_annot, int):
    raise ParseError(
        error_prefix
        + "table annotation is expected to be an integer, not %s (a %s)."
        % (table_annot, type(table_annot))
    )
  if not isinstance(rule_annot, int):
    raise ParseError(
        error_prefix
        + "rule annotation is expected to be an integer, not %s (a %s)."
        % (rule_annot, type(rule_annot))
    )
  if table_annot != table_idx or rule_annot != rule_idx:
    raise ParseError(
        error_prefix
        + "Annotation is for rule %s in table %s." % (rule_annot, table_annot)
    )

  patterns = rule["patterns"]
  actions = rule["actions"]

  if not is_stringlist(patterns):
    raise ParseError(
        "Invalid patterns field: "
        + str(patterns)
        + ". Expected a list of strings."
    )

  if not isinstance(actions, Sequence) or not all(
      [is_strdict(a) for a in actions]
  ):
    raise ParseError(
        "Invalid actions field: "
        + str(actions)
        + ". Expected a list of json objects whose entries are strings."
    )

  patterns = [parse_pattern(pat) for pat in cast(Sequence[str], patterns)]
  actions = set(
      [
          parse_action(action)
          for action in cast(Sequence[Mapping[str, str]], actions)
      ]
  )
  return (patterns, actions)


def parse_table(table_idx: int, table: object) -> d.Table:
  if not isinstance(table, Sequence):
    raise ParseError(
        "Error parsing table %s: Each table is expected to be a list of rules."
        % table
    )
  return [
      parse_rule(table_idx, rule_idx, rule)
      for rule_idx, rule in enumerate(cast(Sequence[object], table))
  ]


def parse_tcam(tcam: object) -> d.TCAM:
  if not isinstance(tcam, Sequence):
    raise ParseError("Each TCAM is expected to be a list of tables.")
  return [
      parse_table(i, table)
      for i, table in enumerate(cast(Sequence[object], tcam))
  ]


# Validation pass: ensure all rules have the same "shape", i.e. the same
# number of patterns of the same bitwidth, in the same order
def validate_tcam(tcam: d.TCAM) -> None:
  first_patterns = tcam[0][0][0]  # Patterns of the first rule in the TCAM
  expected_shape = [p.value.length for p in first_patterns]
  for table in tcam:
    for rule in table:
      shape = [p.value.length for p in rule[0]]
      if shape != expected_shape:
        raise ParseError(
            "All patterns must have the same 'shape'. The following pattern has"
            " a different shape from the first pattern in the table: "
            + str(rule[0])
        )


def parse_ir(jsn: str, from_file: bool) -> d.TCAM:
  if from_file:
    with open(jsn) as f:
      content = json.load(f)
  else:
    content = json.loads(jsn)
  tcam = parse_tcam(content)
  validate_tcam(tcam)
  return tcam
