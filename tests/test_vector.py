"""Test vector operations."""

import numpy as np

from map_machine.geometry.vector import Polyline, compute_angle, turn_by_angle

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

ROOT: float = np.sqrt(2)


def test_compute_angle() -> None:
    """Test angle computing for all angles between 0 and 2π with step π / 4."""
    assert np.allclose(compute_angle(np.array((1, 0))), 0)
    assert np.allclose(compute_angle(np.array((ROOT, ROOT))), np.pi * 0.25)
    assert np.allclose(compute_angle(np.array((0, 1))), np.pi * 0.5)
    assert np.allclose(compute_angle(np.array((-ROOT, ROOT))), np.pi * 0.75)
    assert np.allclose(compute_angle(np.array((-1, 0))), np.pi)
    assert np.allclose(compute_angle(np.array((-ROOT, -ROOT))), np.pi * 1.25)
    assert np.allclose(compute_angle(np.array((0, -1))), np.pi * 1.5)
    assert np.allclose(compute_angle(np.array((ROOT, -ROOT))), np.pi * 1.75)


def test_turn_by_compute_angle() -> None:
    """Test turing one angle by another."""
    assert np.allclose(
        turn_by_angle(np.array((1, 0)), np.pi / 2), np.array((0, 1))
    )


def test_polyline_length() -> None:
    """Test polyline length computation."""
    points = [np.array((0.0, 0.0)), np.array((3.0, 4.0))]
    polyline = Polyline(points)
    assert np.isclose(polyline.length(), 5.0)


def test_polyline_length_multi_segment() -> None:
    """Test polyline length with multiple segments."""
    points = [
        np.array((0.0, 0.0)),
        np.array((3.0, 0.0)),
        np.array((3.0, 4.0)),
    ]
    polyline = Polyline(points)
    assert np.isclose(polyline.length(), 7.0)


def test_polyline_is_left_to_right() -> None:
    """Test polyline direction detection."""
    ltr = Polyline([np.array((0.0, 0.0)), np.array((10.0, 0.0))])
    assert ltr.is_left_to_right()

    rtl = Polyline([np.array((10.0, 0.0)), np.array((0.0, 0.0))])
    assert not rtl.is_left_to_right()

    vertical = Polyline([np.array((5.0, 0.0)), np.array((5.0, 10.0))])
    assert vertical.is_left_to_right()


def test_polyline_reversed() -> None:
    """Test polyline reversal."""
    p = Polyline([np.array((0.0, 0.0)), np.array((10.0, 5.0))])
    r = p.reversed()
    assert np.allclose(r.points[0], np.array((10.0, 5.0)))
    assert np.allclose(r.points[1], np.array((0.0, 0.0)))
    # Original should be unchanged.
    assert np.allclose(p.points[0], np.array((0.0, 0.0)))
