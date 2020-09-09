"""
Author: Sergey Vartanov (me@enzet.ru).
"""

from roentgen.flinger import map_
from roentgen.grid import draw_grid


def test_flinger_map():
    assert map_(5, 0, 10, 0, 20) == 10


def test_icons():
    draw_grid()
