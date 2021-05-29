"""
Test color functions.
"""
from colour import Color

from roentgen.color import is_bright, get_gradient_color
from roentgen.util import MinMax

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def test_is_bright() -> None:
    """
    Test detecting color brightness.
    """
    assert is_bright(Color("white"))
    assert is_bright(Color("yellow"))
    assert not is_bright(Color("brown"))
    assert not is_bright(Color("black"))


def test_gradient() -> None:
    """
    Test color picking from gradient.
    """
    assert (
        get_gradient_color(0.5, MinMax(0, 1), [Color("black"), Color("white")])
        == Color("#7F7F7F")
    )
