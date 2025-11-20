"""Test zoom level specification parsing."""

from map_machine.slippy.tile import (
    ScaleConfigurationException,
    parse_zoom_level,
)

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def test_zoom_level_1() -> None:
    """Test one zoom level."""
    assert parse_zoom_level("18") == [18]


def test_zoom_level_list() -> None:
    """Test list of zoom levels."""
    assert parse_zoom_level("17,18") == [17, 18]
    assert parse_zoom_level("16,17,18") == [16, 17, 18]


def test_zoom_level_range() -> None:
    """Test range of zoom levels."""
    assert parse_zoom_level("16-18") == [16, 17, 18]
    assert parse_zoom_level("18-18") == [18]


def test_zoom_level_mixed() -> None:
    """Test zoom level specification with list of numbers and ranges."""
    assert parse_zoom_level("15,16-18") == [15, 16, 17, 18]
    assert parse_zoom_level("15,16-18,20") == [15, 16, 17, 18, 20]


def test_zoom_level_too_big() -> None:
    """Test too big zoom level."""
    try:
        parse_zoom_level("21")
    except ScaleConfigurationException:
        return

    assert False


def test_zoom_level_negative() -> None:
    """Test negative zoom level."""
    try:
        parse_zoom_level("-1")
    except ValueError:
        return

    assert False


def test_zoom_level_wrong() -> None:
    """Test too big zoom level."""
    try:
        parse_zoom_level(",")
    except ValueError:
        return

    assert False
