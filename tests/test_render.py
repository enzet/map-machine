"""Test rendering of a map."""

import tempfile

import numpy as np
import svgwrite
from svgwrite.path import Path as SVGPath

from map_machine.constructor import Constructor
from map_machine.geometry.bounding_box import BoundingBox
from map_machine.geometry.flinger import MercatorFlinger
from map_machine.map_configuration import MapConfiguration
from map_machine.mapper import Map
from map_machine.osm.osm_reader import OSMData, OSMNode
from map_machine.scheme import Scheme
from tests import workspace


def render(tags: dict[str, str]) -> svgwrite.Drawing:
    """Render a map."""
    osm_data: OSMData = OSMData({1: OSMNode(tags, 1, np.array([0.005, 0.005]))})

    bounding_box: BoundingBox = BoundingBox(0, 0, 0.01, 0.01)
    size: list[float] = [100, 100]
    svg: svgwrite.Drawing = svgwrite.Drawing(tempfile.mkstemp(".svg"), size)
    flinger: MercatorFlinger = MercatorFlinger(
        bounding_box, 18, osm_data.equator_length
    )
    configuration: MapConfiguration = MapConfiguration(
        Scheme.from_file(workspace.DEFAULT_SCHEME_PATH)
    )
    constructor: Constructor = Constructor(
        osm_data=osm_data, flinger=flinger, configuration=configuration
    )
    constructor.construct()

    map_: Map = Map(flinger=flinger, svg=svg, configuration=configuration)
    map_.draw(constructor)
    return svg


def test_render_color() -> None:
    """Test rendering of a map."""
    svg: svgwrite.Drawing = render({"natrual": "tree", "colour": "red"})

    assert isinstance(svg.elements[3], SVGPath)
