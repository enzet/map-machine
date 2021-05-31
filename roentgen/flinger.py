"""
Geo projection.
"""
from typing import Optional

import numpy as np

from roentgen.util import MinMax

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

EQUATOR_LENGTH: float = 40_075_017  # (in meters)


def angle(vector: np.array):
    """
    For the given vector compute an angle between it and (1, 0) vector.  The
    result is in [0, 2π].
    """
    if vector[0] < 0:
        return np.arctan(vector[1] / vector[0]) + np.pi
    if vector[1] < 0:
        return np.arctan(vector[1] / vector[0]) + 2 * np.pi
    else:
        return np.arctan(vector[1] / vector[0])


def turn_by_angle(vector: np.array, angle: float):
    """
    Turn vector by an angle.
    """
    return np.array((
        vector[0] * np.cos(angle) - vector[1] * np.sin(angle),
        vector[0] * np.sin(angle) + vector[1] * np.cos(angle),
    ))


def norm(vector: np.array) -> np.array:
    """
    Compute vector with the same direction and length 1.
    """
    return vector / np.linalg.norm(vector)


def pseudo_mercator(coordinates: np.array) -> np.array:
    """
    Use spherical pseudo-Mercator projection to convert geo coordinates into
    plane.

    :param coordinates: geo positional in the form of (latitude, longitude)
    :return: position on the plane in the form of (x, y)
    """
    return np.array((coordinates[1], 180 / np.pi * np.log(
        np.tan(np.pi / 4 + coordinates[0] * (np.pi / 180) / 2))))


def osm_zoom_level_to_pixels_per_meter(zoom_level: float):
    """
    Convert OSM zoom level (see https://wiki.openstreetmap.org/wiki/Zoom_levels)
    to pixels per meter on Equator.
    """
    return 2 ** zoom_level / 156415


class Flinger:
    """
    Convert geo coordinates into SVG position points.
    """

    def __init__(
        self,
        geo_boundaries: MinMax,
        scale: float = 18,
        border: np.array = np.array((0, 0)),
    ):
        """
        :param geo_boundaries: minimum and maximum latitude and longitude
        :param scale: OSM zoom level
        """
        self.geo_boundaries: MinMax = geo_boundaries
        self.border = border
        self.ratio: float = (
            osm_zoom_level_to_pixels_per_meter(scale) *
            EQUATOR_LENGTH / 360)
        self.size: np.array = self.ratio * (
            pseudo_mercator(self.geo_boundaries.max_) -
            pseudo_mercator(self.geo_boundaries.min_)) + border * 2
        self.pixels_per_meter = osm_zoom_level_to_pixels_per_meter(scale)

        self.size: np.array = self.size.astype(int).astype(float)

    def fling(self, coordinates: np.array) -> np.array:
        """
        Convert geo coordinates into SVG position points.

        :param coordinates: vector to fling
        """
        result: np.array = self.ratio * (
            pseudo_mercator(coordinates) -
            pseudo_mercator(self.geo_boundaries.min_)) + self.border

        # Invert y axis on coordinate plane.
        result[1] = self.size[1] - result[1]

        return result

    def get_scale(self, coordinates: Optional[np.array] = None) -> float:
        """
        Return pixels per meter ratio for the given geo coordinates.

        :param coordinates: geo coordinates
        """
        if coordinates is None:
            # Get pixels per meter ratio for the center of the boundary box.
            coordinates = self.geo_boundaries.center()

        scale_factor: float = 1 / np.cos(coordinates[0] / 180 * np.pi)
        return self.pixels_per_meter * scale_factor
