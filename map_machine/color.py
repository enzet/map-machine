"""Color utility."""

from colour import Color

from map_machine.util import ElementType, MinMax

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

BRIGHTNESS_THRESHOLD: float = 0.78125


def is_bright(color: Color) -> bool:
    """Check whether color is bright enough to have black outline.

    Otherwise it should have white outline.
    """
    return (
        0.2126 * color.red + 0.7152 * color.green + 0.0722 * color.blue
        > BRIGHTNESS_THRESHOLD
    )


def get_gradient_color(
    value: ElementType, bounds: MinMax, colors: list[Color]
) -> Color:
    """Get color from the color scale for the value.

    :param value: given value (should be in bounds)
    :param bounds: maximum and minimum values
    :param colors: color scale
    """
    color_length: int = len(colors) - 1
    scale: list[Color] = [*colors, Color("black")]

    range_coefficient: float = (
        0.0 if bounds.is_empty() else (value - bounds.min_) / bounds.delta()
    )
    # If value is out of range, set it to boundary value.
    range_coefficient = min(1.0, max(0.0, range_coefficient))
    index: int = int(range_coefficient * color_length)
    coefficient: float = (
        range_coefficient - index / color_length
    ) * color_length

    return Color(
        rgb=[
            scale[index].rgb[i]
            + coefficient * (scale[index + 1].rgb[i] - scale[index].rgb[i])
            for i in range(3)
        ]
    )
