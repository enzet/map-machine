"""Geo projection."""
from typing import Optional

import numpy as np

from map_machine.geometry.boundary_box import BoundaryBox

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def pseudo_mercator(coordinates: np.ndarray) -> np.ndarray:
    """
    Use spherical pseudo-Mercator projection to convert geo coordinates.

    The result is (x, y), where x is a longitude value, so x is in [-180, 180],
    and y is a stretched latitude and may have any real value:
    (-infinity, +infinity).

    :param coordinates: geo positional in the form of (latitude, longitude)
    :return: position on the plane in the form of (x, y)
    """
    latitude, longitude = coordinates

    y: float = (
        180.0 / np.pi * np.log(np.tan(np.pi / 4.0 + latitude * np.pi / 360.0))
    )
    return np.array((longitude, y))


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
    return 2.0 ** zoom_level / equator_length * 256.0


class Flinger:
    """Interface for flinger that converts coordinates."""

    def __init__(self, size: np.ndarray) -> None:
        self.size: np.ndarray = size

    def fling(self, coordinates: np.ndarray) -> np.ndarray:
        """Do nothing but return coordinates unchanged."""
        return coordinates

    def get_scale(self, coordinates: Optional[np.ndarray] = None) -> float:
        return 1.0


class MercatorFlinger(Flinger):
    """Convert geographical coordinates into (x, y) points on the plane."""

    def __init__(
        self,
        geo_boundaries: BoundaryBox,
        zoom_level: float,
        equator_length: float,
    ) -> None:
        """
        Initialize flinger with geo boundary box and zoom level.

        :param geo_boundaries: minimum and maximum latitude and longitude
        :param zoom_level: zoom level in OpenStreetMap terminology
        :param equator_length: celestial body equator length in meters
        """
        self.geo_boundaries: BoundaryBox = geo_boundaries
        self.ratio: float = 2.0 ** zoom_level * 256.0 / 360.0
        size: np.ndarray = self.ratio * (
            pseudo_mercator(self.geo_boundaries.max_())
            - pseudo_mercator(self.geo_boundaries.min_())
        )
        self.pixels_per_meter: float = osm_zoom_level_to_pixels_per_meter(
            zoom_level, equator_length
        )
        size = size.astype(int).astype(float)

        super().__init__(size)

        self.min_ = self.ratio * pseudo_mercator(self.geo_boundaries.min_())

    def fling(self, coordinates: np.ndarray) -> np.ndarray:
        """
        Convert geo coordinates into (x, y) position points on the plane.

        :param coordinates: geographical coordinates to fling in the form of
            (latitude, longitude)
        """
        result: np.ndarray = (
            self.ratio * pseudo_mercator(coordinates) - self.min_
        )

        # Invert y axis on coordinate plane.
        result[1] = self.size[1] - result[1]

        return result

    def get_scale(self, coordinates: Optional[np.ndarray] = None) -> float:
        """
        Return pixels per meter ratio for the given geo coordinates.

        :param coordinates: geographical coordinates in the form of
            (latitude, longitude)
        """
        if coordinates is None:
            # Get pixels per meter ratio for the center of the boundary box.
            coordinates = self.geo_boundaries.center()

        scale_factor: float = abs(1.0 / np.cos(coordinates[0] / 180.0 * np.pi))
        return self.pixels_per_meter * scale_factor


class TranslateFlinger(Flinger):
    def __init__(
        self, size: np.ndarray, scale: np.ndarray, offset: np.ndarray
    ) -> None:
        super().__init__(size)
        self.scale: np.ndarray = scale
        self.offset: np.ndarray = offset

    def fling(self, coordinates: np.ndarray) -> np.ndarray:
        return self.scale * (coordinates + self.offset)
