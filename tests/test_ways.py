"""
Test map generation for ways.

Tests check that for the given ways described by tags, Map Machine generates
expected figures in the expected order.
"""
import numpy as np

from map_machine.constructor import Constructor
from map_machine.figure import Figure
from map_machine.geometry.boundary_box import BoundaryBox
from map_machine.geometry.flinger import Flinger
from map_machine.map_configuration import MapConfiguration
from map_machine.osm.osm_reader import OSMData, OSMWay, OSMNode, Tags
from tests import SCHEME, SHAPE_EXTRACTOR


def get_constructor(osm_data: OSMData) -> Constructor:
    flinger: Flinger = Flinger(
        BoundaryBox(-0.01, -0.01, 0.01, 0.01), 18, osm_data.equator_length
    )
    constructor: Constructor = Constructor(
        osm_data, flinger, SCHEME, SHAPE_EXTRACTOR, MapConfiguration()
    )
    constructor.construct_ways()
    return constructor


def create_way(tags: Tags, index: int) -> OSMWay:
    """Create simple OSM way with two arbitrary nodes."""
    nodes: list[OSMNode] = [
        OSMNode({}, 1, np.array((-0.01, -0.01))),
        OSMNode({}, 2, np.array((0.01, 0.01))),
    ]
    return OSMWay(tags, index, nodes)


def test_river_and_wood() -> None:
    """
    Check that river is above the wood.

    See https://github.com/enzet/map-machine/issues/126
    """
    osm_data: OSMData = OSMData()
    osm_data.add_way(create_way({"natural": "wood"}, 1))
    osm_data.add_way(create_way({"waterway": "river"}, 2))

    figures: list[Figure] = get_constructor(osm_data).get_sorted_figures()

    assert len(figures) == 2
    assert figures[0].tags["natural"] == "wood"
    assert figures[1].tags["waterway"] == "river"


def test_empty_ways() -> None:
    """Ways without nodes."""
    osm_data: OSMData = OSMData()
    osm_data.add_way(OSMWay({"natural": "wood"}, 1))
    osm_data.add_way(OSMWay({"waterway": "river"}, 2))

    assert not get_constructor(osm_data).get_sorted_figures()
