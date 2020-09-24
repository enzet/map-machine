"""
Röntgen project. Color utility.

Author: Sergey Vartanov (me@enzet.ru)
"""
from typing import Any, List

from colour import Color

from roentgen.util import MinMax


def is_bright(color: Color) -> bool:
    """
    Is color bright enough to have black outline instead of white.
    """
    return (
        0.2126 * color.red + 0.7152 * color.green + 0.0722 * color.blue
        > 0.78125)


def get_gradient_color(value: Any, bounds: MinMax, colors: List[Color]):
    """
    Get color from the color scale for the value.

    :param value: given value (should be in bounds)
    :param bounds: maximum and minimum values
    :param colors: color scale
    """
    color_length: int = len(colors) - 1
    scale = colors + [Color("black")]

    coefficient: float = (
        0 if bounds.max_ == bounds.min_ else
        (value - bounds.min_) / (bounds.max_ - bounds.min_))
    coefficient = min(1.0, max(0.0, coefficient))
    index: int = int(coefficient * color_length)
    color_coefficient = (coefficient - index / color_length) * color_length

    return Color(rgb=[
        scale[index].rgb[i] + color_coefficient *
        (scale[index + 1].rgb[i] - scale[index].rgb[i]) for i in range(3)])
