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
