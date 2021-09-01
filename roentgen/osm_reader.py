"""
Parse OSM XML file.
"""
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

import numpy as np

from roentgen.boundary_box import BoundaryBox
from roentgen.util import MinMax

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

OSM_TIME_PATTERN: str = "%Y-%m-%dT%H:%M:%SZ"

METERS_PATTERN = re.compile("^(?P<value>\\d*\\.?\\d*)\\s*m$")
KILOMETERS_PATTERN = re.compile("^(?P<value>\\d*\\.?\\d*)\\s*km$")
MILES_PATTERN = re.compile("^(?P<value>\\d*\\.?\\d*)\\s*mi$")


# See https://wiki.openstreetmap.org/wiki/Lifecycle_prefix#Stages_of_decay
STAGES_OF_DECAY: list[str] = [
    "disused",
    "abandoned",
    "ruins",
    "demolished",
    "removed",
    "razed",
    "destroyed",
    "was",  # is not actually a stage of decay
]


def parse_float(string: str) -> Optional[float]:
    """Parse string representation of a float or integer value."""
    try:
        return float(string)
    except (TypeError, ValueError):
        return None


@dataclass
class Tagged:
    """
    Something with tags (string to string mapping).
    """

    tags: dict[str, str]

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
        """Parse float from tag value."""
        if key in self.tags:
            return parse_float(self.tags[key])
        return None

    def get_length(self, key: str) -> Optional[float]:
        """Get length in meters."""
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
            matcher: re.Match = pattern.match(value)
            if matcher:
                float_value: float = parse_float(matcher.group("value"))
                if float_value is not None:
                    return float_value * ratio

        return None


@dataclass
class OSMNode(Tagged):
    """
    OpenStreetMap node.

    See https://wiki.openstreetmap.org/wiki/Node
    """

    id_: int
    coordinates: np.ndarray
    visible: Optional[str] = None
    changeset: Optional[str] = None
    timestamp: Optional[datetime] = None
    user: Optional[str] = None
    uid: Optional[str] = None

    @classmethod
    def from_xml_structure(cls, element: Element) -> "OSMNode":
        """Parse node from OSM XML `<node>` element."""
        attributes = element.attrib
        tags: dict[str, str] = dict(
            [(x.attrib["k"], x.attrib["v"]) for x in element if x.tag == "tag"]
        )
        return cls(
            tags,
            int(attributes["id"]),
            np.array((float(attributes["lat"]), float(attributes["lon"]))),
            attributes["visible"] if "visible" in attributes else None,
            attributes["changeset"] if "changeset" in attributes else None,
            datetime.strptime(attributes["timestamp"], OSM_TIME_PATTERN)
            if "timestamp" in attributes
            else None,
            attributes["user"] if "user" in attributes else None,
            attributes["uid"] if "uid" in attributes else None,
        )

    @classmethod
    def parse_from_structure(cls, structure: dict[str, Any]) -> "OSMNode":
        """
        Parse node from Overpass-like structure.

        :param structure: input structure
        """
        return cls(
            structure["id"],
            structure["tags"] if "tags" in structure else {},
            coordinates=np.array((structure["lat"], structure["lon"])),
        )


@dataclass
class OSMWay(Tagged):
    """
    OpenStreetMap way.

    See https://wiki.openstreetmap.org/wiki/Way
    """

    id_: int
    nodes: Optional[list[OSMNode]] = field(default_factory=list)
    visible: Optional[str] = None
    changeset: Optional[str] = None
    timestamp: Optional[datetime] = None
    user: Optional[str] = None
    uid: Optional[str] = None

    @classmethod
    def from_xml_structure(
        cls, element: Element, nodes: dict[int, OSMNode]
    ) -> "OSMWay":
        """Parse way from OSM XML `<way>` element."""
        attributes = element.attrib
        tags: dict[str, str] = dict(
            [(x.attrib["k"], x.attrib["v"]) for x in element if x.tag == "tag"]
        )
        return cls(
            tags,
            int(element.attrib["id"]),
            [nodes[int(x.attrib["ref"])] for x in element if x.tag == "nd"],
            attributes["visible"] if "visible" in attributes else None,
            attributes["changeset"] if "changeset" in attributes else None,
            datetime.strptime(attributes["timestamp"], OSM_TIME_PATTERN)
            if "timestamp" in attributes
            else None,
            attributes["user"] if "user" in attributes else None,
            attributes["uid"] if "uid" in attributes else None,
        )

    @classmethod
    def parse_from_structure(
        cls, structure: dict[str, Any], nodes: dict[int, OSMNode]
    ) -> "OSMWay":
        """
        Parse way from Overpass-like structure.

        :param structure: input structure
        :param nodes: node structure
        """
        return cls(
            structure["tags"],
            structure["id"],
            [nodes[x] for x in structure["nodes"]],
        )

    def is_cycle(self) -> bool:
        """Is way a cycle way or an area boundary."""
        return self.nodes[0] == self.nodes[-1]

    def __repr__(self) -> str:
        return f"Way <{self.id_}> {self.nodes}"


@dataclass
class OSMMember:
    """
    Member of OpenStreetMap relation.
    """

    type_: str
    ref: int
    role: str


@dataclass
class OSMRelation(Tagged):
    """
    OpenStreetMap relation.

    See https://wiki.openstreetmap.org/wiki/Relation
    """

    id_: int
    members: Optional[list[OSMMember]]
    visible: Optional[str] = None
    changeset: Optional[str] = None
    timestamp: Optional[datetime] = None
    user: Optional[str] = None
    uid: Optional[str] = None

    @classmethod
    def from_xml_structure(cls, element: Element) -> "OSMRelation":
        """Parse relation from OSM XML `<relation>` element."""
        attributes = element.attrib
        members: list[OSMMember] = []
        tags: dict[str, str] = {}
        for subelement in element:
            if subelement.tag == "member":
                subattributes = subelement.attrib
                members.append(
                    OSMMember(
                        subattributes["type"],
                        int(subattributes["ref"]),
                        subattributes["role"],
                    )
                )
            if subelement.tag == "tag":
                tags[subelement.attrib["k"]] = subelement.attrib["v"]
        return cls(
            tags,
            int(attributes["id"]),
            members,
            attributes["visible"] if "visible" in attributes else None,
            attributes["changeset"] if "changeset" in attributes else None,
            datetime.strptime(attributes["timestamp"], OSM_TIME_PATTERN)
            if "timestamp" in attributes
            else None,
            attributes["user"] if "user" in attributes else None,
            attributes["uid"] if "uid" in attributes else None,
        )

    @classmethod
    def parse_from_structure(cls, structure: dict[str, Any]) -> "OSMRelation":
        """
        Parse relation from Overpass-like structure.

        :param structure: input structure
        """
        return cls(
            structure["tags"],
            structure["id"],
            [
                OSMMember(x["type"], x["role"], x["ref"])
                for x in structure["members"]
            ],
        )


class NotWellFormedOSMDataException(Exception):
    """
    OSM data structure is not well-formed.
    """

    pass


class OSMData:
    """
    The whole OpenStreetMap information about nodes, ways, and relations.
    """

    def __init__(self) -> None:
        self.nodes: dict[int, OSMNode] = {}
        self.ways: dict[int, OSMWay] = {}
        self.relations: dict[int, OSMRelation] = {}

        self.authors: set[str] = set()
        self.time: MinMax = MinMax()
        self.view_box: Optional[BoundaryBox] = None

    def add_node(self, node: OSMNode) -> None:
        """Add node and update map parameters."""
        if node.id_ in self.nodes:
            raise NotWellFormedOSMDataException(
                f"Node with duplicate id {node.id_}."
            )
        self.nodes[node.id_] = node
        if node.user:
            self.authors.add(node.user)
        self.time.update(node.timestamp)

    def add_way(self, way: OSMWay) -> None:
        """Add way and update map parameters."""
        if way.id_ in self.ways:
            raise NotWellFormedOSMDataException(
                f"Way with duplicate id {way.id_}."
            )
        self.ways[way.id_] = way
        if way.user:
            self.authors.add(way.user)
        self.time.update(way.timestamp)

    def add_relation(self, relation: OSMRelation) -> None:
        """Add relation and update map parameters."""
        if relation.id_ in self.relations:
            raise NotWellFormedOSMDataException(
                f"Relation with duplicate id {relation.id_}."
            )
        self.relations[relation.id_] = relation


class OverpassReader:
    """
    Reader for JSON structure extracted from Overpass API.

    See https://wiki.openstreetmap.org/wiki/Overpass_API
    """

    def __init__(self) -> None:
        self.osm_data = OSMData()

    def parse_json_file(self, file_name: Path) -> OSMData:
        """Parse JSON structure from the file and construct map."""
        with file_name.open() as input_file:
            structure = json.load(input_file)

        node_map = {}
        way_map = {}

        for element in structure["elements"]:
            if element["type"] == "node":
                node = OSMNode.parse_from_structure(element)
                node_map[node.id_] = node
                self.osm_data.add_node(node)
        for element in structure["elements"]:
            if element["type"] == "way":
                way = OSMWay.parse_from_structure(element, node_map)
                way_map[way.id_] = way
                self.osm_data.add_way(way)
        for element in structure["elements"]:
            if element["type"] == "relation":
                relation = OSMRelation.parse_from_structure(element)
                self.osm_data.add_relation(relation)

        return self.osm_data


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
    ) -> None:
        """
        :param parse_nodes: whether nodes should be parsed
        :param parse_ways:  whether ways should be parsed
        :param parse_relations: whether relations should be parsed
        """
        self.osm_data = OSMData()
        self.parse_nodes: bool = parse_nodes
        self.parse_ways: bool = parse_ways
        self.parse_relations: bool = parse_relations

    def parse_osm_file(self, file_name: Path) -> OSMData:
        """
        Parse OSM XML file.

        :param file_name: input XML file
        :return: parsed map
        """
        return self.parse_osm(ElementTree.parse(file_name).getroot())

    def parse_osm_text(self, text: str) -> OSMData:
        """
        Parse OSM XML data from text representation.

        :param text: XML text representation
        :return: parsed map
        """
        return self.parse_osm(ElementTree.fromstring(text))

    def parse_osm(self, root: Element) -> OSMData:
        """
        Parse OSM XML data.

        :param root: top element of XML data
        :return: parsed map
        """
        for element in root:
            if element.tag == "bounds":
                self.parse_bounds(element)
            if element.tag == "node" and self.parse_nodes:
                node = OSMNode.from_xml_structure(element)
                self.osm_data.add_node(node)
            if element.tag == "way" and self.parse_ways:
                self.osm_data.add_way(
                    OSMWay.from_xml_structure(element, self.osm_data.nodes)
                )
            if element.tag == "relation" and self.parse_relations:
                self.osm_data.add_relation(
                    OSMRelation.from_xml_structure(element)
                )
        return self.osm_data

    def parse_bounds(self, element: Element) -> None:
        """Parse view box from XML element."""
        attributes = element.attrib
        self.osm_data.view_box = BoundaryBox(
            float(attributes["minlon"]),
            float(attributes["minlat"]),
            float(attributes["maxlon"]),
            float(attributes["maxlat"]),
        )
