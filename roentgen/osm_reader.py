"""
Reading OpenStreetMap data from XML file.
"""
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import numpy as np

from roentgen.util import MinMax

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

OSM_TIME_PATTERN: str = "%Y-%m-%dT%H:%M:%SZ"

METERS_PATTERN = re.compile("^(?P<value>\\d*\\.?\\d*)\\s*m$")
KILOMETERS_PATTERN = re.compile("^(?P<value>\\d*\\.?\\d*)\\s*km$")
MILES_PATTERN = re.compile("^(?P<value>\\d*\\.?\\d*)\\s*mi$")


def parse_float(string: str) -> Optional[float]:
    """
    Parse string representation of a float or integer value.
    """
    try:
        return float(string)
    except (TypeError, ValueError):
        return None


class Tagged:
    """
    OpenStreetMap element (node, way or relation) with tags.
    """

    def __init__(self):
        self.tags: Dict[str, str] = {}

    def get_tag(self, key: str) -> Optional[str]:
        """
        Get tag value or None if it doesn't exist.

        :param key: tag key
        :return: tag value or None
        """
        if key in self.tags:
            return self.tags[key]
        return None

    def get_float(self, key: str) -> Optional[float]:
        if key in self.tags:
            return parse_float(self.tags[key])
        return None

    def get_length(self, key: str) -> Optional[float]:
        """
        Get length in meters.
        """
        if key not in self.tags:
            return None

        value: str = self.tags[key]

        float_value: float = parse_float(value) 
        if float_value is not None:
            return float_value

        for pattern, ratio in [
            (METERS_PATTERN, 1.0),
            (KILOMETERS_PATTERN, 1000.0),
            (MILES_PATTERN, 1609.344),
        ]:
            matcher = pattern.match(value)
            if matcher:
                float_value: float = parse_float(matcher.group("value")) 
                if float_value is not None:
                    return float_value * ratio

        return None


class OSMNode(Tagged):
    """
    OpenStreetMap node.

    See https://wiki.openstreetmap.org/wiki/Node
    """

    def __init__(self):
        super().__init__()

        self.id_: Optional[int] = None
        self.coordinates: Optional[np.array] = None

        self.visible: Optional[str] = None
        self.changeset: Optional[str] = None
        self.timestamp: Optional[datetime] = None
        self.user: Optional[str] = None
        self.uid: Optional[str] = None

    @classmethod
    def from_xml_structure(cls, element, is_full: bool = False) -> "OSMNode":
        """
        Parse node from OSM XML `<node>` element.
        """
        node = cls()
        attributes = element.attrib
        node.id_ = int(attributes["id"])
        node.coordinates = np.array(
            (float(attributes["lat"]), float(attributes["lon"]))
        )
        if is_full:
            node.visible = attributes["visible"]
            node.changeset = attributes["changeset"]
            node.timestamp = datetime.strptime(
                attributes["timestamp"], OSM_TIME_PATTERN
            )
            node.user = attributes["user"]
            node.uid = attributes["uid"]
        for subelement in element:
            if subelement.tag == "tag":
                subattributes = subelement.attrib
                node.tags[subattributes["k"]] = subattributes["v"]
        return node

    def parse_from_structure(self, structure: Dict[str, Any]) -> "OSMNode":
        """
        Parse node from Overpass-like structure.

        :param structure: input structure
        """
        self.id_ = structure["id"]
        self.coordinates = np.array((structure["lat"], structure["lon"]))
        if "tags" in structure:
            self.tags = structure["tags"]

        return self


class OSMWay(Tagged):
    """
    OpenStreetMap way.

    See https://wiki.openstreetmap.org/wiki/Way
    """

    def __init__(self, id_: int = 0, nodes: Optional[List[OSMNode]] = None):
        super().__init__()

        self.id_: int = id_
        self.nodes: List[OSMNode] = [] if nodes is None else nodes

        self.visible: Optional[str] = None
        self.changeset: Optional[str] = None
        self.user: Optional[str] = None
        self.timestamp: Optional[datetime] = None
        self.uid: Optional[str] = None

    @classmethod
    def from_xml_structure(cls, element, nodes, is_full: bool) -> "OSMWay":
        """
        Parse way from OSM XML `<way>` element.
        """
        way = cls(int(element.attrib["id"]))
        if is_full:
            way.visible = element.attrib["visible"]
            way.changeset = element.attrib["changeset"]
            way.timestamp = datetime.strptime(
                element.attrib["timestamp"], OSM_TIME_PATTERN
            )
            way.user = element.attrib["user"]
            way.uid = element.attrib["uid"]
        for subelement in element:
            if subelement.tag == "nd":
                way.nodes.append(nodes[int(subelement.attrib["ref"])])
            if subelement.tag == "tag":
                way.tags[subelement.attrib["k"]] = subelement.attrib["v"]
        return way

    def parse_from_structure(
        self, structure: Dict[str, Any], nodes
    ) -> "OSMWay":
        """
        Parse way from Overpass-like structure.

        :param structure: input structure
        :param nodes: node structure
        """
        self.id_ = structure["id"]
        for node_id in structure["nodes"]:
            self.nodes.append(nodes[node_id])
        if "tags" in structure:
            self.tags = structure["tags"]

        return self

    def is_cycle(self) -> bool:
        """
        Is way a cycle way or an area boundary.
        """
        return self.nodes[0] == self.nodes[-1]

    def try_to_glue(self, other: "OSMWay") -> Optional["OSMWay"]:
        """
        Create new combined way if ways share endpoints.
        """
        if self.nodes[0] == other.nodes[0]:
            return OSMWay(nodes=list(reversed(other.nodes[1:])) + self.nodes)
        if self.nodes[0] == other.nodes[-1]:
            return OSMWay(nodes=other.nodes[:-1] + self.nodes)
        if self.nodes[-1] == other.nodes[-1]:
            return OSMWay(nodes=self.nodes + list(reversed(other.nodes[:-1])))
        if self.nodes[-1] == other.nodes[0]:
            return OSMWay(nodes=self.nodes + other.nodes[1:])
        return None

    def __repr__(self) -> str:
        return f"Way <{self.id_}> {self.nodes}"


class OSMRelation(Tagged):
    """
    OpenStreetMap relation.

    See https://wiki.openstreetmap.org/wiki/Relation
    """

    def __init__(self, id_: int = 0):
        super().__init__()

        self.id_: int = id_
        self.members: List["OSMMember"] = []
        self.user: Optional[str] = None
        self.timestamp: Optional[datetime] = None

    @classmethod
    def from_xml_structure(cls, element, is_full: bool) -> "OSMRelation":
        """
        Parse relation from OSM XML `<relation>` element.
        """
        attributes = element.attrib
        relation = cls(int(attributes["id"]))
        if is_full:
            relation.user = attributes["user"]
            relation.timestamp = datetime.strptime(
                attributes["timestamp"], OSM_TIME_PATTERN
            )
        for subelement in element:
            if subelement.tag == "member":
                subattributes = subelement.attrib
                relation.members.append(
                    OSMMember(
                        subattributes["type"],
                        int(subattributes["ref"]),
                        subattributes["role"],
                    )
                )
            if subelement.tag == "tag":
                relation.tags[subelement.attrib["k"]] = subelement.attrib["v"]
        return relation

    def parse_from_structure(self, structure: Dict[str, Any]) -> "OSMRelation":
        """
        Parse relation from Overpass-like structure.

        :param structure: input structure
        """
        self.id_ = structure["id"]
        for member in structure["members"]:
            mem = OSMMember()
            mem.type_ = member["type"]
            mem.role = member["role"]
            mem.ref = member["ref"]
            self.members.append(mem)
        if "tags" in structure:
            self.tags = structure["tags"]

        return self


@dataclass
class OSMMember:
    """
    Member of OpenStreetMap relation.
    """

    type_: str = ""
    ref: int = 0
    role: str = ""


class Map:
    """
    The whole OpenStreetMap information about nodes, ways, and relations.
    """

    def __init__(self):
        self.nodes: Dict[int, OSMNode] = {}
        self.ways: Dict[int, OSMWay] = {}
        self.relations: Dict[int, OSMRelation] = {}

        self.authors: Set[str] = set()
        self.time: MinMax = MinMax()
        self.boundary_box: List[MinMax] = [MinMax(), MinMax()]

    def add_node(self, node: OSMNode) -> None:
        """
        Add node and update map parameters.
        """
        self.nodes[node.id_] = node
        if node.user:
            self.authors.add(node.user)
        self.time.update(node.timestamp)
        self.boundary_box[0].update(node.coordinates[0])
        self.boundary_box[1].update(node.coordinates[1])

    def add_way(self, way: OSMWay) -> None:
        """
        Add way and update map parameters.
        """
        self.ways[way.id_] = way
        if way.user:
            self.authors.add(way.user)
        self.time.update(way.timestamp)

    def add_relation(self, relation: OSMRelation) -> None:
        """
        Add relation and update map parameters.
        """
        self.relations[relation.id_] = relation


class OverpassReader:
    """
    Reader for JSON structure extracted from Overpass API.

    See https://wiki.openstreetmap.org/wiki/Overpass_API
    """

    def __init__(self):
        self.map_ = Map()

    def parse_json_file(self, file_name: Path) -> Map:
        """
        Parse JSON structure from the file and construct map.
        """
        with file_name.open() as input_file:
            structure = json.load(input_file)

        node_map = {}
        way_map = {}

        for element in structure["elements"]:
            if element["type"] == "node":
                node = OSMNode().parse_from_structure(element)
                node_map[node.id_] = node
                self.map_.add_node(node)
        for element in structure["elements"]:
            if element["type"] == "way":
                way = OSMWay().parse_from_structure(element, node_map)
                way_map[way.id_] = way
                self.map_.add_way(way)
        for element in structure["elements"]:
            if element["type"] == "relation":
                relation = OSMRelation().parse_from_structure(element)
                self.map_.add_relation(relation)

        return self.map_


class OSMReader:
    """
    OpenStreetMap XML file parser.

    See https://wiki.openstreetmap.org/wiki/OSM_XML
    """

    def __init__(
        self,
        parse_nodes: bool = True,
        parse_ways: bool = True,
        parse_relations: bool = True,
        is_full: bool = False,
    ):
        """
        :param parse_nodes: whether nodes should be parsed
        :param parse_ways:  whether ways should be parsed
        :param parse_relations: whether relations should be parsed
        :param is_full: whether metadata should be parsed: tags `visible`,
            `changeset`, `timestamp`, `user`, `uid`
        """
        self.map_ = Map()
        self.parse_nodes: bool = parse_nodes
        self.parse_ways: bool = parse_ways
        self.parse_relations: bool = parse_relations
        self.is_full: bool = is_full

    def parse_osm_file(self, file_name: Path) -> Map:
        """
        Parse OSM XML file.

        :param file_name: input XML file
        :return: parsed map
        """
        return self.parse_osm(ET.parse(file_name).getroot())

    def parse_osm_text(self, text: str) -> Map:
        """
        Parse OSM XML data from text representation.

        :param text: XML text representation
        :return: parsed map
        """
        return self.parse_osm(ET.fromstring(text))

    def parse_osm(self, root) -> Map:
        """
        Parse OSM XML data.

        :param root: root of XML data
        :return: parsed map
        """
        for element in root:
            if element.tag == "node" and self.parse_nodes:
                node = OSMNode.from_xml_structure(element, self.is_full)
                self.map_.add_node(node)
            if element.tag == "way" and self.parse_ways:
                self.map_.add_way(
                    OSMWay.from_xml_structure(
                        element, self.map_.nodes, self.is_full
                    )
                )
            if element.tag == "relation" and self.parse_relations:
                self.map_.add_relation(
                    OSMRelation.from_xml_structure(element, self.is_full)
                )
        return self.map_
