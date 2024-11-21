"""
Test map generation for ways.

Tests check that for the given ways described by tags, Map Machine generates
expected figures in the expected order.
"""

import numpy as np

from map_machine.constructor import Constructor
from map_machine.figure import Figure
from map_machine.geometry.boundary_box import BoundaryBox
from map_machine.geometry.flinger import MercatorFlinger
from map_machine.map_configuration import MapConfiguration
from map_machine.osm.osm_reader import OSMData, OSMWay, OSMNode, Tags
from tests import SCHEME, SHAPE_EXTRACTOR

CONFIGURATION: MapConfiguration = MapConfiguration(SCHEME)


def get_constructor(osm_data: OSMData) -> Constructor:
    """
    Get custom constructor for bounds (-0.01, -0.01, 0.01, 0.01) and zoom level
    18.
    """
    flinger: MercatorFlinger = MercatorFlinger(
        BoundaryBox(-0.01, -0.01, 0.01, 0.01), 18, osm_data.equator_length
    )
    constructor: Constructor = Constructor(
        osm_data, flinger, SHAPE_EXTRACTOR, CONFIGURATION
    )
    constructor.construct_ways()
    return constructor


def create_way(osm_data: OSMData, tags: Tags, index: int) -> None:
    """Create simple OSM way with two arbitrary nodes."""
    nodes: list[OSMNode] = [
        OSMNode({}, 1, np.array((-0.01, -0.01))),
        OSMNode({}, 2, np.array((0.01, 0.01))),
    ]
    for node in nodes:
        osm_data.add_node(node)
    osm_data.add_way(OSMWay(tags, index, nodes))


def test_river_and_wood() -> None:
    """
    Check that river is above the wood.

    See https://github.com/enzet/map-machine/issues/126
    """
    osm_data: OSMData = OSMData()
    create_way(osm_data, {"natural": "wood"}, 1)
    create_way(osm_data, {"waterway": "river"}, 2)

    figures: list[Figure] = get_constructor(osm_data).get_sorted_figures()

    assert len(figures) == 2
    assert figures[0].tags["natural"] == "wood"
    assert figures[1].tags["waterway"] == "river"


def test_placement_and_lanes() -> None:
    """
    Check that `placement` tag is processed correctly when `lanes` tag is not
    specified.

    See https://github.com/enzet/map-machine/issues/128
    """
    osm_data: OSMData = OSMData()
    create_way(osm_data, {"highway": "motorway", "placement": "right_of:2"}, 1)

    get_constructor(osm_data)


def test_empty_ways() -> None:
    """Ways without nodes."""
    osm_data: OSMData = OSMData()
    osm_data.add_way(OSMWay({"natural": "wood"}, 1))
    osm_data.add_way(OSMWay({"waterway": "river"}, 2))

    assert not get_constructor(osm_data).get_sorted_figures()
