"""Tests for length tag parsing."""

from typing import Optional

from map_machine.osm.osm_reader import Tagged

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def check_length(value: str, expected: Optional[float]) -> None:
    """Assert that constructed value is equals to an expected one."""
    tagged = Tagged({"a": value})
    assert tagged.get_length("a") == expected


def test_meters() -> None:
    """Test length in meters processing."""
    check_length("50m", 50.0)
    check_length("50.m", 50.0)
    check_length("50.05m", 50.05)
    check_length(".05m", 0.05)
    check_length(".m", None)
    check_length("50   m", 50.0)


def test_kilometers() -> None:
    """Test length in meters processing."""
    check_length("50km", 50_000.0)
    check_length("50 km", 50_000.0)


def test_miles() -> None:
    """Test length in meters processing."""
    check_length("1mi", 1609.344)
    check_length("50 mi", 50 * 1609.344)
