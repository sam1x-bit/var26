from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import xml.etree.ElementTree as ET

from lark import Lark, Transformer, UnexpectedInput, v_args


class ConfigLangError(Exception):
    pass


class ConfigLangSyntaxError(ConfigLangError):
    pass


class ConfigLangEvalError(ConfigLangError):
    pass


@dataclass(frozen=True)
class Number:
    raw: str


@dataclass(frozen=True)
class Ref:
    name: str


@dataclass(frozen=True)
class Define:
    name: str
    value: Expr


@dataclass(frozen=True)
class DictNode:
    items: List[Tuple[str, Expr]]


Expr = Number | Ref | Define | DictNode


_GRAMMAR = r"""
start: program

program: expr+

?expr: dict
     | define
     | ref
     | NUMBER           -> number

dict: "{" pairs? "}"
pairs: pair ("," pair)* ","?
pair: NAME "=" expr

define: "(" "define" NAME expr ")"
ref: "." "[" NAME "]" "."

NUMBER: /[+-]?\d+\.?\d*[eE][+-]?\d+/
NAME: /[a-z]+/

%import common.WS
%ignore WS
"""


_PARSER = Lark(_GRAMMAR, start="start", parser="lalr")


@v_args(inline=True)
class _AstBuilder(Transformer):
    def number(self, token):
        return Number(str(token))

    def ref(self, name):
        return Ref(str(name))

    def define(self, name, value):
        return Define(str(name), value)

    def pair(self, name, value):
        return (str(name), value)

    def pairs(self, first, *rest):
        return [first, *rest]

    def dict(self, pairs=None):
        return DictNode(pairs or [])

    def program(self, *exprs):
        return list(exprs)

    def start(self, program):
        return program


def parse_program(text: str) -> List[Expr]:
    try:
        tree = _PARSER.parse(text)
        return _AstBuilder().transform(tree)
    except UnexpectedInput as e:
        raise ConfigLangSyntaxError(str(e)) from e


def _parse_number(raw: str) -> int | float:
    if any(c in raw for c in (".", "e", "E")):
        return float(raw)
    return int(raw)


def eval_program(exprs: List[Expr]) -> Any:
    if not exprs:
        raise ConfigLangEvalError("empty input")

    env: Dict[str, Any] = {}
    config: Dict[str, Any] = {}
    has_config = False
    last: Any = None
    for expr in exprs:
        value = eval_expr(expr, env)
        last = value
        if isinstance(expr, DictNode):
            has_config = True
            for key, item_value in value.items():
                if key in config:
                    raise ConfigLangEvalError(f"duplicate key: {key}")
                config[key] = item_value

    return config if has_config else last


def eval_expr(expr: Expr, env: Dict[str, Any]) -> Any:
    if isinstance(expr, Number):
        return _parse_number(expr.raw)

    if isinstance(expr, Ref):
        if expr.name not in env:
            raise ConfigLangEvalError(f"undefined constant: {expr.name}")
        return env[expr.name]

    if isinstance(expr, Define):
        if expr.name in env:
            raise ConfigLangEvalError(f"redefinition of constant: {expr.name}")
        value = eval_expr(expr.value, env)
        env[expr.name] = value
        return value

    if isinstance(expr, DictNode):
        result: Dict[str, Any] = {}
        for key, value_expr in expr.items:
            if key in result:
                raise ConfigLangEvalError(f"duplicate key: {key}")
            result[key] = eval_expr(value_expr, env)
        return result

    raise ConfigLangEvalError(f"unsupported expression: {type(expr)!r}")


def parse_and_eval(text: str) -> Any:
    return eval_program(parse_program(text))


def to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def to_xml(value: Any) -> str:
    root = ET.Element("config")
    _value_to_xml(root, value)
    return ET.tostring(root, encoding="unicode")


def _value_to_xml(parent: ET.Element, value: Any) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            child = ET.SubElement(parent, k)
            _value_to_xml(child, v)
        return

    if isinstance(value, (int, float)):
        parent.text = str(value)
        return

    raise ConfigLangEvalError(f"cannot serialize value of type: {type(value)!r}")
