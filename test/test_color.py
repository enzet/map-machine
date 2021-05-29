"""
Test color functions.
"""
from colour import Color

from roentgen.color import is_bright

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

