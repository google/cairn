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

"""Parser for configuration files, which generates the initial MachineState."""

from collections.abc import Mapping, Sequence
import json
from typing import Type, TypeVar

import interpreter.datatypes as d
import interpreter.expression_parser as eparser

ParseError = eparser.ParseError

# Allows dependent typing so we can have one read_field function that reads
# any type, based on its second argument.
T = TypeVar("T")


# Read a json field. Ensure it exists and has the expected type.
def read_field(
    error_prefix: str, obj: Mapping[str, object], name: str, ty: Type[T]
) -> T:
  if name not in obj:
    raise ParseError(error_prefix + "Expected to find %s field." % name)
  val = obj[name]
  if not isinstance(val, ty):
    raise ParseError(
        error_prefix + "Expected %s field to have type %s." % (name, ty)
    )
  return val


def parse_data_store(store: object) -> tuple[str, d.DataStore]:
  """Parse a single data store entry."""
  if not isinstance(store, Mapping):
    raise ParseError(
        "Each entry in the list of data stores should be a dictionary object."
    )
  error_prefix = "Error parsing data store %s: " % store
  name = read_field(error_prefix, store, "name", str)
  width = read_field(error_prefix, store, "width", int)
  read = read_field(error_prefix, store, "read", bool)
  write = read_field(error_prefix, store, "write", bool)
  persistent = read_field(error_prefix, store, "persistent", bool)
  masked_writes = read_field(error_prefix, store, "masked-writes", bool)
  store = d.DataStore(
      value=d.Data(length=width),  # Defaults to all bits 0
      read=read,
      write=write,
      persistent=persistent,
      masked_writes=masked_writes,
  )
  return (name, store)


def parse_data_stores(jsn: Mapping[str, object]) -> dict[str, d.DataStore]:
  if "data stores" not in jsn:
    raise ParseError("No 'data stores' field in configuration file.")
  stores_jsn = jsn["data stores"]
  if not isinstance(stores_jsn, Sequence):
    raise ParseError("'data stores' field should be a list.")
  parsed_stores = [parse_data_store(store) for store in stores_jsn]
  stores = {}
  for name, store in parsed_stores:
    stores[name] = store
  return stores


def parse_key(key: object, parser: eparser.Parser) -> d.Location:
  """Parse a single key, represented as a string."""
  error_prefix = "Failure while parsing key %s: " % key
  if not isinstance(key, str):
    raise ParseError(
        error_prefix + "Each entry in the list of keys should be a string."
    )
  try:
    locexp = parser.parse(key)
  except ParseError as e:
    raise ParseError(error_prefix + ("'%s'" % str(e))) from e
  if not isinstance(locexp.exp, d.LocationExp):
    raise ParseError(error_prefix + "Each key should be a location.")
  if not isinstance(locexp.exp.start.exp, d.SizedInt):
    raise ParseError(
        error_prefix + "Each key should start at a simple integer index."
    )
  if not isinstance(locexp.exp.end.exp, d.SizedInt):
    raise ParseError(
        error_prefix + "Each key should end at a simple integer index."
    )
  start = locexp.exp.start.exp.value
  end = locexp.exp.end.exp.value
  if start > end:
    raise ParseError(
        "Failure while parsing key %s: Start index is greater than end index!"
        % key
    )
  return d.Location(name=locexp.exp.name, start=start, end=end)


def parse_keys(jsn: Mapping[str, object]) -> dict[str, d.Location]:
  if "keys" not in jsn:
    raise ParseError("No 'keys' field in configuration file.")
  keys = jsn["keys"]
  if not isinstance(keys, Sequence):
    raise ParseError("'keys' field should be a list.")
  if len(keys) == 0:
    raise ParseError("'keys' field should be nonempty!")
  key_parser = eparser.Parser()
  keys = [parse_key(key, key_parser) for key in keys]
  return keys


def parse_config(jsn: object) -> d.MachineState:
  """Extract the relevant top-level fields, with appropriate validation."""
  if not isinstance(jsn, Mapping):
    raise ParseError(
        "Configuration files should have a dictionary object at top level."
    )

  stores = parse_data_stores(jsn)
  keys = parse_keys(jsn)

  state = d.MachineState(
      cursor=0, stage=0, stores=stores, keys=keys, headers={}
  )
  return state


def parse(jsn: str, from_file: bool) -> d.MachineState:
  if from_file:
    with open(jsn) as f:
      content = json.load(f)
  else:
    content = json.loads(jsn)
  state = parse_config(content)
  return state
