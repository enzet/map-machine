"""
Author: Sergey Vartanov (me@enzet.ru)
"""
import numpy as np

from roentgen.util import MinMax


EQUATOR_LENGTH: float = 40_075_017


def pseudo_mercator(coordinates: np.array) -> np.array:
    """
    Use spherical pseudo-Mercator projection to convert geo coordinates into
    plane.

    :param coordinates: geo positional in the form of (latitude, longitude)
    :return: position on the plane in the form of (x, y)
    """
    return np.array((coordinates[1], 180 / np.pi * np.log(
        np.tan(np.pi / 4 + coordinates[0] * (np.pi / 180) / 2))))


class Flinger:
    """
    Convert geo coordinates into SVG position points.
    """
    def __init__(self, geo_boundaries: MinMax, ratio: float = 1000):
        """
        :param geo_boundaries: minimum and maximum latitude and longitude
        """
        self.geo_boundaries: MinMax = geo_boundaries
        self.ratio: float = ratio
        self.size: np.array = self.ratio * (
            pseudo_mercator(self.geo_boundaries.max_) -
            pseudo_mercator(self.geo_boundaries.min_))
        self.pixels_per_meter = 360 / EQUATOR_LENGTH * self.ratio

        self.size: np.array = self.size.astype(int).astype(float)

    def fling(self, coordinates: np.array) -> np.array:
        """
        :param coordinates: vector to fling
        """
        result: np.array = self.ratio * (
            pseudo_mercator(coordinates) -
            pseudo_mercator(self.geo_boundaries.min_))

        # Invert y axis on coordinate plane.
        result[1] = self.size[1] - result[1]

        return result

    def get_scale(self, coordinates: np.array) -> float:
        scale_factor = 1 / np.cos(coordinates[0] / 180 * np.pi)
        return self.pixels_per_meter * scale_factor
