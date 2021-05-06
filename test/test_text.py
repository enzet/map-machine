"""
Test text generation.

Author: Sergey Vartanov (me@enzet.ru).
"""
from roentgen.text import format_voltage


def test_voltage() -> None:
    """
    Test voltage tag value processing.
    """
    assert format_voltage("42") == "42 V"
    assert format_voltage("42000") == "42 kV"
