"""Test GPX parsing and bounding box computation."""

from pathlib import Path

import pytest
from gpxpy import gpx as gpxpy_gpx

from map_machine.gpx import get_bounding_box, load_gpx

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

TEST_GPX_PATH: Path = Path("tests/data/test_track.gpx")


def test_load_gpx() -> None:
    """Test loading a GPX file."""
    gpx = load_gpx(TEST_GPX_PATH)
    assert len(gpx.tracks) == 1
    assert gpx.tracks[0].name == "Test Track"
    assert len(gpx.tracks[0].segments) == 1
    assert len(gpx.tracks[0].segments[0].points) == 4


def test_bounding_box_from_gpx() -> None:
    """Test bounding box computation from GPX data."""
    gpx = load_gpx(TEST_GPX_PATH)
    bbox = get_bounding_box(gpx, padding=0.001)

    assert bbox.bottom < 20.0002
    assert bbox.top > 20.0008
    assert bbox.left < 10.0002
    assert bbox.right > 10.0008


def test_bounding_box_padding() -> None:
    """Test that padding expands the bounding box."""
    gpx = load_gpx(TEST_GPX_PATH)
    bbox_small = get_bounding_box(gpx, padding=0.001)
    bbox_large = get_bounding_box(gpx, padding=0.01)

    assert bbox_large.left < bbox_small.left
    assert bbox_large.bottom < bbox_small.bottom
    assert bbox_large.right > bbox_small.right
    assert bbox_large.top > bbox_small.top


def test_bounding_box_empty_gpx() -> None:
    """Test that empty GPX raises ValueError."""
    gpx = gpxpy_gpx.GPX()
    with pytest.raises(ValueError, match="no track points"):
        get_bounding_box(gpx)


def test_bounding_box_too_large() -> None:
    """Test that oversized GPX track raises ValueError."""
    gpx = gpxpy_gpx.GPX()
    track = gpxpy_gpx.GPXTrack()
    segment = gpxpy_gpx.GPXTrackSegment()
    segment.points.append(gpxpy_gpx.GPXTrackPoint(10.0, 10.0))
    segment.points.append(gpxpy_gpx.GPXTrackPoint(11.0, 11.0))
    track.segments.append(segment)
    gpx.tracks.append(track)

    with pytest.raises(ValueError, match="too large"):
        get_bounding_box(gpx)
