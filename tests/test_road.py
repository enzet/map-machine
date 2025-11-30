"""Test road drawing."""

from __future__ import annotations

import numpy as np

from map_machine.feature.road import Road
from map_machine.geometry.bounding_box import BoundingBox
from map_machine.geometry.flinger import MercatorFlinger
from map_machine.osm.osm_reader import OSMData, OSMNode
from map_machine.scheme import RoadMatcher
from tests import SCHEME

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def create_test_road(
    tags: dict[str, str],
    nodes: list[OSMNode] | None = None,
) -> Road:
    """Create a test road with default nodes if not provided."""
    if nodes is None:
        nodes = [
            OSMNode({}, 1, np.array((-0.01, -0.01))),
            OSMNode({}, 2, np.array((0.01, 0.01))),
        ]
    osm_data: OSMData = OSMData()
    for node in nodes:
        osm_data.add_node(node)

    flinger: MercatorFlinger = MercatorFlinger(
        BoundingBox(-0.01, -0.01, 0.01, 0.01), 18, osm_data.equator_length
    )

    road_matcher: RoadMatcher | None = SCHEME.get_road(tags)
    if road_matcher is None:
        # Create a default road matcher if none found.
        road_matcher = RoadMatcher(
            {
                "tags": {"highway": "*"},
                "color": "road_color",
                "border_color": "road_border_color",
                "default_width": 5.0,
            },
            SCHEME,
        )

    return Road(tags, nodes, road_matcher, flinger, SCHEME)


def test_road_creation() -> None:
    """Test basic road creation."""
    road: Road = create_test_road({"highway": "primary"})
    assert road.nodes is not None
    assert len(road.nodes) == 2  # noqa: PLR2004
    assert road.width > 0
    assert road.scale > 0


def test_road_with_lanes() -> None:
    """Test road with lanes tag."""
    lanes: int = 4
    road: Road = create_test_road({"highway": "primary", "lanes": str(lanes)})
    assert len(road.lanes) == lanes
    assert road.width == lanes * 3.7


def test_road_with_width() -> None:
    """Test road with width tag."""
    width: float = 10.5
    road: Road = create_test_road({"highway": "primary", "width": str(width)})
    assert road.width == width


def test_road_with_placement() -> None:
    """Test road with placement tag."""
    lanes: int = 3
    road: Road = create_test_road(
        {"highway": "primary", "lanes": str(lanes), "placement": "right_of:1"}
    )
    assert len(road.lanes) == lanes
    assert road.width == 3.7 * lanes
    assert road.placement_offset != 0.0


def test_road_with_width_lanes() -> None:
    """Test road with width:lanes tag."""
    lanes: int = 2
    road: Road = create_test_road(
        {"highway": "primary", "lanes": str(lanes), "width:lanes": "3.5|4.0"}
    )
    assert len(road.lanes) == lanes
    assert road.lanes[0].width == 3.5  # noqa: PLR2004
    assert road.lanes[1].width == 4.0  # noqa: PLR2004


def test_road_with_lanes_forward() -> None:
    """Test road with lanes:forward tag."""
    lanes: int = 4
    lanes_forward: int = 2
    road: Road = create_test_road(
        {
            "highway": "primary",
            "lanes": str(lanes),
            "lanes:forward": str(lanes_forward),
        }
    )
    assert len(road.lanes) == lanes
    assert road.lanes[-2].is_forward is True
    assert road.lanes[-1].is_forward is True


def test_road_with_lanes_backward() -> None:
    """Test road with lanes:backward tag."""
    lanes: int = 4
    lanes_backward: int = 2
    road: Road = create_test_road(
        {
            "highway": "primary",
            "lanes": str(lanes),
            "lanes:backward": str(lanes_backward),
        }
    )
    assert len(road.lanes) == lanes
    assert road.lanes[0].is_forward is False
    assert road.lanes[1].is_forward is False
