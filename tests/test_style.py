"""Test style constructing for ways and areas."""

from tests import SCHEME

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def test_style_empty() -> None:
    """Test constructing style of empty tags."""
    assert SCHEME.get_style({}) == []


def test_style_unknown() -> None:
    """Test constructing style of unknown tags."""
    assert SCHEME.get_style({"aaa": "bbb"}) == []


def test_style_area() -> None:
    """Test constructing style of landuse=grass."""
    style = SCHEME.get_style({"landuse": "grass"})
    assert len(style) == 1
    assert style[0].style == {"fill": "#CFE0A8", "stroke": "#BFD098"}
