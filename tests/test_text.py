"""Test text generation."""

from map_machine.text import format_voltage

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def test_voltage() -> None:
    """Test voltage tag value processing."""
    assert format_voltage("42") == "42 V"
    assert format_voltage("42000") == "42 kV"
