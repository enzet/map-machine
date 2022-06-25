"""Geo projection."""
from typing import Optional

import numpy as np

from map_machine.geometry.boundary_box import BoundaryBox

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def pseudo_mercator(coordinates: np.ndarray) -> np.ndarray:
    """
    Use spherical pseudo-Mercator projection to convert geo coordinates.

    :param coordinates: geo positional in the form of (latitude, longitude)
    :return: position on the plane in the form of (x, y)
    """
    y: float = (
        180.0
        / np.pi
        * np.log(np.tan(np.pi / 4.0 + coordinates[0] * np.pi / 360.0))
    )
    return np.array((coordinates[1], y))


def osm_zoom_level_to_pixels_per_meter(
    zoom_level: float, equator_length: float
) -> float:
    """
    Convert OSM zoom level to pixels per meter on Equator.

    See https://wiki.openstreetmap.org/wiki/Zoom_levels

    :param zoom_level: integer number usually not bigger than 20, but this
        function allows any non-negative float value
    :param equator_length: celestial body equator length in meters
    """
    return 2.0**zoom_level / equator_length * 256.0


class Flinger:
    """Convert geo coordinates into SVG position points."""

    def __init__(
        self,
        geo_boundaries: BoundaryBox,
        zoom_level: float,
        equator_length: float,
    ) -> None:
        """
        :param geo_boundaries: minimum and maximum latitude and longitude
        :param zoom_level: zoom level in OpenStreetMap terminology
        :param equator_length: celestial body equator length in meters
        """
        self.geo_boundaries: BoundaryBox = geo_boundaries
        self.ratio: float = 2.0**zoom_level * 256.0 / 360.0
        self.size: np.ndarray = self.ratio * (
            pseudo_mercator(self.geo_boundaries.max_())
            - pseudo_mercator(self.geo_boundaries.min_())
        )
        self.pixels_per_meter: float = osm_zoom_level_to_pixels_per_meter(
            zoom_level, equator_length
        )
        self.size: np.ndarray = self.size.astype(int).astype(float)

    def fling(self, coordinates: np.ndarray) -> np.ndarray:
        """
        Convert geo coordinates into SVG position points.

        :param coordinates: vector to fling
        """
        result: np.ndarray = self.ratio * (
            pseudo_mercator(coordinates)
            - pseudo_mercator(self.geo_boundaries.min_())
        )

        # Invert y axis on coordinate plane.
        result[1] = self.size[1] - result[1]

        return result

    def get_scale(self, coordinates: Optional[np.ndarray] = None) -> float:
        """
        Return pixels per meter ratio for the given geo coordinates.

        :param coordinates: geo coordinates
        """
        if coordinates is None:
            # Get pixels per meter ratio for the center of the boundary box.
            coordinates = self.geo_boundaries.center()

        scale_factor: float = abs(1.0 / np.cos(coordinates[0] / 180.0 * np.pi))
        return self.pixels_per_meter * scale_factor
