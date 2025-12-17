import json
import xml.etree.ElementTree as ET

import pytest

from configlang.__main__ import main as cli_main
from configlang.translator import (
    ConfigLangEvalError,
    ConfigLangSyntaxError,
    parse_and_eval,
    to_json,
    to_xml,
)


def test_number_scientific_notation():
    assert parse_and_eval("1e+3") == 1000.0


def test_dict_and_nested_dict():
    value = parse_and_eval("{a=1e+1,b={c=2e+0,},}")
    assert value == {"a": 10.0, "b": {"c": 2.0}}


def test_define_and_ref_across_program():
    value = parse_and_eval("(define x 2e+0) {a=.[x].,}")
    assert value == {"a": 2.0}


def test_define_inside_dict_then_ref():
    value = parse_and_eval("{a=(define x 1e+0), b=.[x].,}")
    assert value == {"a": 1.0, "b": 1.0}


def test_json_contains_keys_and_values():
    value = {"a": 10.0, "b": {"c": 2.0}}
    s = to_json(value)
    assert json.loads(s) == value


def test_xml_contains_keys_and_values():
    value = {"a": 10.0, "b": {"c": 2.0}}
    xml_text = to_xml(value)
    root = ET.fromstring(xml_text)
    assert root.tag == "config"
    assert root.find("a").text == "10.0"
    assert root.find("b").find("c").text == "2.0"


def test_cli_generates_example_files(tmp_path):
    rc = cli_main(["--generate-examples", "--output-dir", str(tmp_path)])
    assert rc == 0

    xml_path = tmp_path / "example.xml"
    assert xml_path.exists()

    json_path = tmp_path / "example.json"
    assert not json_path.exists()

    root = ET.fromstring(xml_path.read_text(encoding="utf-8"))
    assert root.tag == "config"
    assert root.find("service").find("workers").text == "4.0"
    assert root.find("service").find("port").text == "80.0"


def test_undefined_constant_is_error():
    with pytest.raises(ConfigLangEvalError):
        parse_and_eval(".[x].")


def test_redefinition_is_error():
    with pytest.raises(ConfigLangEvalError):
        parse_and_eval("(define x 1e+0) (define x 2e+0)")


def test_syntax_error_is_error():
    with pytest.raises(ConfigLangSyntaxError):
        parse_and_eval("{a=1e+0")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "(define defaultport 8e+1) {service={workers=4e+0,port=.[defaultport].,},}",
            {"service": {"workers": 4.0, "port": 80.0}},
        ),
        (
            "{budget={income=1e+3,expenses={rent=5e+2,food=2e+2,},},}",
            {"budget": {"income": 1000.0, "expenses": {"rent": 500.0, "food": 200.0}}},
        ),
        (
            "(define g 9.8e+0) {experiment={g=.[g].,t=2e+0,},}",
            {"experiment": {"g": 9.8, "t": 2.0}},
        ),
    ],
)
def test_examples_from_three_domains(text, expected):
    assert parse_and_eval(text) == expected
