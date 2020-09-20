from typing import Any, List

from colour import Color


class MinMax:
    """
    Minimum and maximum.
    """
    def __init__(self, min_=None, max_=None):
        self.min_ = min_
        self.max_ = max_

    def update(self, value):
        """
        Update minimum and maximum with new value.
        """
        self.min_ = value if not self.min_ or value < self.min_ else self.min_
        self.max_ = value if not self.max_ or value > self.max_ else self.max_

    def delta(self):
        """
        Difference between maximum and minimum.
        """
        return self.max_ - self.min_

    def center(self):
        """
        Get middle point between minimum and maximum.
        """
        return (self.min_ + self.max_) / 2


def is_bright(color: Color) -> bool:
    """
    Is color bright enough to have black outline instead of white.
    """
    return (
        0.2126 * color.red * 256 +
        0.7152 * color.green * 256 +
        0.0722 * color.blue * 256 > 200)


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
    m: int = int(coefficient * color_length)
    color_coefficient = (coefficient - m / color_length) * color_length

    return Color(rgb=[
        scale[m].rgb[i] + color_coefficient *
        (scale[m + 1].rgb[i] - scale[m].rgb[i]) for i in range(3)])
