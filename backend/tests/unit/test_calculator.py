import pytest
from app.tools.calculator import calculator


def test_addition():
    assert calculator.invoke({"expression": "2 + 2"}) == "4"


def test_subtraction():
    assert calculator.invoke({"expression": "10 - 3"}) == "7"


def test_multiplication():
    assert calculator.invoke({"expression": "6 * 7"}) == "42"


def test_division():
    assert calculator.invoke({"expression": "10 / 4"}) == "2.5"


def test_complex_expression():
    result = calculator.invoke({"expression": "25 * 4 + 100 / 2"})
    assert result == "150"


def test_division_by_zero():
    result = calculator.invoke({"expression": "10 / 0"})
    assert "Error" in result


def test_invalid_expression():
    result = calculator.invoke({"expression": "import os"})
    assert "Error" in result


def test_percentage():
    result = calculator.invoke({"expression": "85 * 0.15"})
    assert result == "12.75"


def test_power():
    assert calculator.invoke({"expression": "2 ** 10"}) == "1024"
