"""Test coordinates computation."""

import numpy as np

from map_machine.geometry.flinger import (
    osm_zoom_level_to_pixels_per_meter,
    pseudo_mercator,
)

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def test_pseudo_mercator() -> None:
    """Test pseudo-Mercator projection."""
    assert np.allclose(pseudo_mercator(np.array((0, 0))), np.array((0, 0)))
    assert np.allclose(pseudo_mercator(np.array((0, 10))), np.array((10, 0)))
    assert np.allclose(
        pseudo_mercator(np.array((10, 0))), np.array((0, 10.05115966))
    )


def test_osm_zoom_level_to_pixels_per_meter() -> None:
    """Test scale computation."""
    assert np.allclose(
        osm_zoom_level_to_pixels_per_meter(18, 40_075_017.0), 1.6745810488364858
    )
