"""
Geo projection.
"""
from typing import Optional

import numpy as np

from roentgen.util import MinMax

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

EQUATOR_LENGTH: float = 40_075_017  # meters


def pseudo_mercator(coordinates: np.array) -> np.array:
    """
    Use spherical pseudo-Mercator projection to convert geo coordinates into
    plane.

    :param coordinates: geo positional in the form of (latitude, longitude)
    :return: position on the plane in the form of (x, y)
    """
    y: float = (
        180 / np.pi * np.log(np.tan(np.pi / 4 + coordinates[0] * np.pi / 360))
    )
    return np.array((coordinates[1], y))


def osm_zoom_level_to_pixels_per_meter(zoom_level: float) -> float:
    """
    Convert OSM zoom level to pixels per meter on Equator. See
    https://wiki.openstreetmap.org/wiki/Zoom_levels

    :param zoom_level: integer number usually not bigger than 20, but this
        function allows any non-negative float value
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
    ) -> None:
        """
        :param geo_boundaries: minimum and maximum latitude and longitude
        :param scale: OSM zoom level
        """
        self.geo_boundaries: MinMax = geo_boundaries
        self.border = border
        self.ratio: float = (
            osm_zoom_level_to_pixels_per_meter(scale) * EQUATOR_LENGTH / 360
        )
        self.size: np.array = border * 2 + self.ratio * (
            pseudo_mercator(self.geo_boundaries.max_)
            - pseudo_mercator(self.geo_boundaries.min_)
        )
        self.pixels_per_meter = osm_zoom_level_to_pixels_per_meter(scale)

        self.size: np.array = self.size.astype(int).astype(float)

    def fling(self, coordinates: np.array) -> np.array:
        """
        Convert geo coordinates into SVG position points.

        :param coordinates: vector to fling
        """
        result: np.array = self.border + self.ratio * (
            pseudo_mercator(coordinates)
            - pseudo_mercator(self.geo_boundaries.min_)
        )

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
