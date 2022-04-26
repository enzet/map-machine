import numpy as np

from map_machine.figure import Figure
from map_machine.geometry.boundary_box import BoundaryBox
from map_machine.geometry.flinger import Flinger
from map_machine.map_configuration import MapConfiguration
from map_machine.constructor import Constructor
from map_machine.osm.osm_reader import OSMData, OSMWay, OSMNode
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


def test_river_and_wood() -> None:
    """
    Check that river is above the wood.

    See https://github.com/enzet/map-machine/issues/126
    """
    nodes_1: list[OSMNode] = [
        OSMNode({}, 1, np.array((-0.01, -0.01))),
        OSMNode({}, 2, np.array((0.01, 0.01))),
    ]
    nodes_2: list[OSMNode] = [
        OSMNode({}, 3, np.array((-0.01, -0.01))),
        OSMNode({}, 4, np.array((0.01, 0.01))),
    ]

    osm_data: OSMData = OSMData()
    osm_data.add_way(OSMWay({"natural": "wood"}, 1, nodes_1))
    osm_data.add_way(OSMWay({"waterway": "river"}, 2, nodes_2))

    figures: list[Figure] = get_constructor(osm_data).get_sorted_figures()

    assert len(figures) == 2
    assert figures[0].tags["natural"] == "wood"
    assert figures[1].tags["waterway"] == "river"
