"""Test OSM XML parsing."""

import numpy as np

from map_machine.osm.osm_reader import (
    OSMData,
    OSMNode,
    OSMRelation,
    OSMWay,
    parse_levels,
)

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def test_node() -> None:
    """Test OSM node parsing from XML."""
    osm_data: OSMData = OSMData()
    osm_data.parse_osm_text(
        """<?xml version="1.0"?>
<osm>
  <node id="42" lon="5" lat="10" />
</osm>"""
    )
    assert 42 in osm_data.nodes
    node: OSMNode = osm_data.nodes[42]
    assert node.id_ == 42
    assert np.allclose(node.coordinates, np.array([10, 5]))


def test_node_with_tag() -> None:
    """Test OSM node parsing from XML."""
    osm_data: OSMData = OSMData()
    osm_data.parse_osm_text(
        """<?xml version="1.0"?>
<osm>
  <node id="42" lon="5" lat="10">
    <tag k="key" v="value" />
  </node>
</osm>"""
    )
    assert 42 in osm_data.nodes
    node: OSMNode = osm_data.nodes[42]
    assert node.id_ == 42
    assert np.allclose(node.coordinates, np.array([10, 5]))
    assert node.tags["key"] == "value"


def test_way() -> None:
    """Test OSM way parsing from XML."""
    osm_data: OSMData = OSMData()
    osm_data.parse_osm_text(
        """<?xml version="1.0"?>
<osm>
  <way id="42" />
</osm>"""
    )
    assert 42 in osm_data.ways
    way: OSMWay = osm_data.ways[42]
    assert way.id_ == 42


def test_nodes() -> None:
    """Test OSM node parsing from XML."""
    osm_data: OSMData = OSMData()
    osm_data.parse_osm_text(
        """<?xml version="1.0"?>
<osm>
  <node id="1" lon="5" lat="10" />
  <way id="2">
    <nd ref="1" />
    <tag k="key" v="value" />
  </way>
</osm>"""
    )
    way: OSMWay = osm_data.ways[2]
    assert len(way.nodes) == 1
    assert way.nodes[0].id_ == 1
    assert way.tags["key"] == "value"


def test_relation() -> None:
    """Test OSM node parsing from XML."""
    osm_data: OSMData = OSMData()
    osm_data.parse_osm_text(
        """<?xml version="1.0"?>
<osm>
  <node id="1" lon="5" lat="10" />
  <way id="2">
    <nd ref="1" />
  </way>
  <relation id="3">
    <member type="way" ref="2" role="outer" />
    <tag k="key" v="value" />
  </relation>
</osm>"""
    )
    assert 3 in osm_data.relations
    relation: OSMRelation = osm_data.relations[3]
    assert relation.id_ == 3
    assert relation.tags["key"] == "value"
    assert len(relation.members) == 1
    assert relation.members[0].type_ == "way"
    assert relation.members[0].ref == 2


def test_parse_levels() -> None:
    """Test level parsing."""
    assert parse_levels("1") == [1]
    assert parse_levels("-1") == [-1]
    assert parse_levels("1.5") == [1.5]
    assert parse_levels("1,5") == [1.5]


def test_parse_levels_list() -> None:
    """Test list of levels parsing."""
    assert parse_levels("0;1") == [0, 1]
    assert parse_levels("0;2") == [0, 2]
    assert parse_levels("0;2.5") == [0, 2.5]
    assert parse_levels("0;2,5") == [0, 2.5]
