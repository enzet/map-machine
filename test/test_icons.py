"""
Author: Sergey Vartanov (me@enzet.ru).
"""
from os import makedirs

from roentgen.grid import draw_all_icons


def test_icons() -> None:
    """ Test grid drawing. """
    makedirs("icon_set", exist_ok=True)
    draw_all_icons("temp.svg", "icon_set")
