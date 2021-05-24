"""
Test style constructing for ways and areas.
"""
from test import SCHEME

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def test_style_empty() -> None:
    """
    Test constructing style of empty tags.
    """
    assert SCHEME.get_style({}, 18) == []


def test_style_unknown() -> None:
    """
    Test constructing style of unknown tags.
    """
    assert SCHEME.get_style({"aaa": "bbb"}, 18) == []


def test_style_area() -> None:
    """
    Test constructing style of landuse=grass.
    """
    style = SCHEME.get_style({"landuse": "grass"}, 18)
    assert len(style) == 1
    assert style[0].style == {"fill": "#CFE0A8", "stroke": "#BFD098"}
