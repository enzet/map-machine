"""
Test OSM XML parsing.
"""
import numpy as np
from roentgen.osm_reader import OSMNode, OSMReader, OSMRelation, OSMWay


def test_node() -> None:
    """
    Test OSM node parsing from XML.
    """
    reader = OSMReader()
    map_ = reader.parse_osm_text(
        """<?xml version="1.0"?>
<osm>
  <node id="42" lon="5" lat="10" />
</osm>"""
    )
    assert 42 in map_.node_map
    node: OSMNode = map_.node_map[42]
    assert node.id_ == 42
    assert np.allclose(node.coordinates, np.array([10, 5]))


def test_node_with_tag() -> None:
    """
    Test OSM node parsing from XML.
    """
    reader = OSMReader()
    map_ = reader.parse_osm_text(
        """<?xml version="1.0"?>
<osm>
  <node id="42" lon="5" lat="10">
    <tag k="key" v="value" />
  </node>
</osm>"""
    )
    assert 42 in map_.node_map
    node: OSMNode = map_.node_map[42]
    assert node.id_ == 42
    assert np.allclose(node.coordinates, np.array([10, 5]))
    assert node.tags["key"] == "value"


def test_way() -> None:
    """
    Test OSM way parsing from XML.
    """
    reader = OSMReader()
    map_ = reader.parse_osm_text(
        """<?xml version="1.0"?>
<osm>
  <way id="42" />
</osm>"""
    )
    assert 42 in map_.way_map
    way: OSMWay = map_.way_map[42]
    assert way.id_ == 42


def test_nodes() -> None:
    """
    Test OSM node parsing from XML.
    """
    reader = OSMReader()
    map_ = reader.parse_osm_text(
        """<?xml version="1.0"?>
<osm>
  <node id="1" lon="5" lat="10" />
  <way id="2">
    <nd ref="1" />
    <tag k="key" v="value" />
  </way>
</osm>"""
    )
    way: OSMWay = map_.way_map[2]
    assert len(way.nodes) == 1
    assert way.nodes[0].id_ == 1
    assert way.tags["key"] == "value"


def test_relation() -> None:
    """
    Test OSM node parsing from XML.
    """
    reader = OSMReader()
    map_ = reader.parse_osm_text(
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
    assert 3 in map_.relation_map
    relation: OSMRelation = map_.relation_map[3]
    assert relation.id_ == 3
    assert relation.tags["key"] == "value"
    assert len(relation.members) == 1
    assert relation.members[0].type_ == "way"
    assert relation.members[0].ref == 2
