"""
Author: Sergey Vartanov (me@enzet.ru).
"""

from roentgen.grid import draw_all_icons


def test_icons() -> None:
    """ Test grid drawing. """
    draw_all_icons("temp.svg")
