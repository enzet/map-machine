"""GPX file loading and bounding box computation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import gpxpy
import gpxpy.gpx

from map_machine.geometry.bounding_box import (
    LATITUDE_MAX_DIFFERENCE,
    LONGITUDE_MAX_DIFFERENCE,
    BoundingBox,
)

if TYPE_CHECKING:
    from pathlib import Path

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

logger: logging.Logger = logging.getLogger(__name__)

DEFAULT_PADDING: float = 0.005


def load_gpx(path: Path) -> gpxpy.gpx.GPX:
    """Parse a GPX file.

    :param path: path to the GPX file
    :return: parsed GPX data
    """
    with path.open(encoding="utf-8") as gpx_file:
        return gpxpy.parse(gpx_file)


def get_bounding_box(
    gpx: gpxpy.gpx.GPX, padding: float = DEFAULT_PADDING
) -> BoundingBox:
    """Compute bounding box from GPX track points with padding.

    :param gpx: parsed GPX data
    :param padding: padding in degrees around the track
    :return: bounding box covering all track points
    :raises ValueError: if the GPX has no track points or the resulting
        bounding box exceeds the size limit
    """
    bounds = gpx.get_bounds()
    if (
        bounds is None
        or bounds.min_longitude is None
        or bounds.min_latitude is None
        or bounds.max_longitude is None
        or bounds.max_latitude is None
    ):
        message = "GPX file contains no track points."
        raise ValueError(message)

    left: float = bounds.min_longitude - padding
    bottom: float = bounds.min_latitude - padding
    right: float = bounds.max_longitude + padding
    top: float = bounds.max_latitude + padding

    if (
        right - left > LONGITUDE_MAX_DIFFERENCE
        or top - bottom > LATITUDE_MAX_DIFFERENCE
    ):
        message = (
            f"GPX track bounding box is too large "
            f"({right - left:.3f}° × {top - bottom:.3f}°). "
            f"Maximum allowed is "
            f"{LONGITUDE_MAX_DIFFERENCE}° × {LATITUDE_MAX_DIFFERENCE}°."
        )
        raise ValueError(message)

    return BoundingBox(left, bottom, right, top)
