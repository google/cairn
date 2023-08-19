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

"""Parse integer expressions that are contained in IR files.

Since IntExps are currently context-free, not regular, we can't use regexes to
parse them. Instead, we use the simple lex+yacc implementation in the ply
package. Doing so involves definings a lexer and a parser grammar. The first is
done in the Lexer class, and the latter in the Parser class.

Much of this code is copied from the example file at
http://www.dabeaz.com/ply/ply.html#ply_nn1 as well as the stackoverflow answer
https://stackoverflow.com/questions/38262552/how-to-encapsulate-the-lex-and-yacc-of-ply-in-two-seperate-class
"""

from typing import cast

import interpreter.datatypes as d
from ply import lex
from ply import yacc


class ParseError(Exception):
  pass


class Lexer:
  """The lexer defines the tokens used by the parser.

  In ply, this is done using several specially-named class members.
  """

  # The set of tokens. Each will be assigned a value during lexing, which
  # will be used during parsing
  tokens = (
      'NUMBER',
      'PLUS',
      'MINUS',
      'LSHIFT',
      'RSHIFT',
      'ID',
      'CAST',
  )

  # Tokens that aren't assigned a value. They can be thought of as 'just' syntax
  literals = ['[', ']', ':', '(', ')']

  # Defines the form of the ID token as a regex, value is the matched string
  t_ID = r'[a-zA-Z_][a-zA-Z_0-9]*'

  # Defines the form of the PLUS token, value is an d.ArithOp
  def t_PLUS(self, t):
    r'\+'
    t.value = d.ArithOp.PLUS
    return t

  def t_MINUS(self, t):
    r'\-'
    t.value = d.ArithOp.MINUS
    return t

  def t_LSHIFT(self, t):
    r'<<'
    t.value = d.ArithOp.LSHIFT
    return t

  def t_RSHIFT(self, t):
    r'>>'
    t.value = d.ArithOp.RSHIFT
    return t

  def t_CAST(self, t):
    r'\(w[0-9]+\)'
    num = cast(str, t.value)[2:-1]
    t.value = int(num)
    if t.value == 0:
      raise ParseError('Casts are not allowed to have 0 width!')
    return t

  # NUMBER tokens may or may not specify a width. If not, default to 32 bits.
  def t_NUMBER(self, t):
    r'[0-9]+(w[0-9]+)?'
    nums = cast(str, t.value).split('w')
    if len(nums) > 1:
      size = int(nums[1])
    else:
      size = 32
    t.value = d.SizedInt(int(nums[0]), size)
    return t

  # Characters we ignore (spaces and tabs)
  t_ignore = ' \t'

  # If we see a character we don't recognize, throw an error
  def t_error(self, t):
    raise ParseError("Illegal character '%s'" % cast(str, t.value)[0])

  def __init__(self):
    self.lexer = lex.lex(module=self)


class Parser:
  """Parser for integer expressions.

  The parser is defined by creating a set of member functions representing
  grammar rules. The docstring defines the grammar, and the body of the function
  defines the produced value (the LHS) in terms of the value(s) of the LHS.
  """

  tokens = Lexer.tokens

  # All operations are left-associative
  precedence = (
      ('left', 'LSHIFT', 'RSHIFT'),  # Lowest precedence
      ('left', 'PLUS', 'MINUS'),
      ('nonassoc', 'CAST'),  # Highest precedence
  )

  # Grammar rules are defined as functions. The t parameter represents the rule;
  # t[0] is the value of the LHS (to be set by the function), and other params
  # are the values of each entry on the right. The | separator creates new rules
  # so the docstring here defines 3 rules, each of which is only one entry long.
  def p_intexp(self, t):
    """intexp : constexp
              | locexp
              | arithexp"""

    # Set the value of the intexp (the LHS) to the value of the first thing on
    # the RHS (the constexp/locexp/arithexp)
    t[0] = d.IntExp(t[1])

  # Allow parens around expressions for precedence
  def p_intexp_parens(self, t):
    """intexp : '(' intexp ')'"""

    # We reference t[2] here because the intexp is the second thing on the RHS
    t[0] = t[2]

  def p_constexp(self, t):
    """constexp : NUMBER"""

    # The value of a NUMBER is a SizedInt
    t[0] = t[1]

  def p_locexp(self, t):
    """locexp : ID '[' intexp ':' intexp ']'"""

    name = t[1]  # The ID value
    start = t[3]  # the first intexp
    end = t[5]  # the second intexp

    t[0] = d.LocationExp(name, start, end)

  def p_arithexp(self, t):
    """arithexp : intexp PLUS intexp
                | intexp MINUS intexp
                | intexp LSHIFT intexp
                | intexp RSHIFT intexp
                | CAST intexp
    """
    # We have to have casts and binops in the same rule to ensure precedence
    # works properly
    if len(t) == 3:  # Cast
      t[0] = d.ArithExp(
          d.ArithOp.CAST, d.IntExp(d.SizedInt(t[1], 32)), t[2]
      )
    else:  # Binop
      t[0] = d.ArithExp(t[2], t[1], t[3])

  def p_error(self, t):
    raise ParseError("Unable to parse '%s'" % cast(str, t.value)[0])

  def __init__(self):
    self.lexer = Lexer()
    self.parser = yacc.yacc(module=self, debug=False, write_tables=False)

  def parse(self, s: str) -> d.IntExp:
    return self.parser.parse(s)
