"""Parse OSM XML file."""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

import numpy as np

from map_machine.geometry.boundary_box import BoundaryBox
from map_machine.util import MinMax

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

OSM_TIME_PATTERN: str = "%Y-%m-%dT%H:%M:%SZ"

METERS_PATTERN: re.Pattern = re.compile("^(?P<value>\\d*\\.?\\d*)\\s*m$")
KILOMETERS_PATTERN: re.Pattern = re.compile("^(?P<value>\\d*\\.?\\d*)\\s*km$")
MILES_PATTERN: re.Pattern = re.compile("^(?P<value>\\d*\\.?\\d*)\\s*mi$")

EARTH_EQUATOR_LENGTH: float = 40_075_017.0

Tags = dict[str, str]

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


def parse_levels(string: str) -> list[float]:
    """Parse string representation of level sequence value."""
    # TODO: add `-` parsing
    try:
        return list(map(float, string.replace(",", ".").split(";")))
    except ValueError:
        logging.warning(f"Cannot parse level description from `{string}`.")
        return []


@dataclass
class Tagged:
    """Something with tags (string to string mapping)."""

    tags: Tags

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

    def verify(self) -> bool:
        """Check key and value types."""
        is_well_formed: bool = True

        for value, key in self.tags.items():
            if not isinstance(key, str):
                logging.warning(f"Not string key {key}.")
                is_well_formed = False
            if not isinstance(value, str):
                logging.warning(f"Not string value {value}.")
                is_well_formed = False

        return is_well_formed


@dataclass(eq=False)
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
        tags: Tags = {
            x.attrib["k"]: x.attrib["v"] for x in element if x.tag == "tag"
        }
        return cls(
            tags,
            int(attributes["id"]),
            np.array((float(attributes["lat"]), float(attributes["lon"]))),
            attributes.get("visible", None),
            attributes.get("changeset", None),
            (
                datetime.strptime(attributes["timestamp"], OSM_TIME_PATTERN)
                if "timestamp" in attributes
                else None
            ),
            attributes.get("user", None),
            attributes.get("uid", None),
        )

    @classmethod
    def parse_from_structure(cls, structure: dict[str, Any]) -> "OSMNode":
        """
        Parse node from Overpass-like structure.

        :param structure: input structure
        """
        return cls(
            structure.get("tags", {}),
            structure["id"],
            coordinates=np.array((structure["lat"], structure["lon"])),
        )

    def get_boundary_box(self) -> BoundaryBox:
        return BoundaryBox(
            self.coordinates[1],
            self.coordinates[0],
            self.coordinates[1],
            self.coordinates[0],
        )

    def __hash__(self) -> int:
        return self.id_

    def __eq__(self, other) -> bool:
        if not isinstance(other, OSMNode):
            return False
        return (
            self.id_ == other.id_
            and np.array_equal(self.coordinates, other.coordinates)
            and self.visible == other.visible
            and self.changeset == other.changeset
            and self.timestamp == other.timestamp
            and self.user == other.user
            and self.uid == other.uid
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
        tags: Tags = {
            x.attrib["k"]: x.attrib["v"] for x in element if x.tag == "tag"
        }
        return cls(
            tags,
            int(element.attrib["id"]),
            [nodes[int(x.attrib["ref"])] for x in element if x.tag == "nd"],
            attributes.get("visible", None),
            attributes.get("changeset", None),
            (
                datetime.strptime(attributes["timestamp"], OSM_TIME_PATTERN)
                if "timestamp" in attributes
                else None
            ),
            attributes.get("user", None),
            attributes.get("uid", None),
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
            structure.get("tags", {}),
            structure["id"],
            [nodes[x] for x in structure["nodes"]],
        )

    def is_cycle(self) -> bool:
        """Is way a cycle way or an area boundary."""
        return self.nodes[0] == self.nodes[-1]

    def __repr__(self) -> str:
        return f"Way <{self.id_}> {self.nodes}"

    def __hash__(self) -> int:
        return self.id_


@dataclass
class OSMMember:
    """Member of OpenStreetMap relation."""

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
        tags: Tags = {}
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
            attributes.get("visible", None),
            attributes.get("changeset", None),
            (
                datetime.strptime(attributes["timestamp"], OSM_TIME_PATTERN)
                if "timestamp" in attributes
                else None
            ),
            attributes.get("user", None),
            attributes.get("uid", None),
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
                OSMMember(x["type"], x["ref"], x["role"])
                for x in structure["members"]
            ],
        )


class NotWellFormedOSMDataException(Exception):
    """OSM data structure is not well-formed."""


class OSMData:
    """The whole OpenStreetMap information about nodes, ways, and relations."""

    def __init__(self) -> None:
        self.nodes: dict[int, OSMNode] = {}
        self.ways: dict[int, OSMWay] = {}
        self.relations: dict[int, OSMRelation] = {}

        self.authors: set[str] = set()
        self.levels: set[float] = set()
        self.time: MinMax = MinMax()
        self.view_box: Optional[BoundaryBox] = None
        self.boundary_box: Optional[BoundaryBox] = None
        self.equator_length: float = EARTH_EQUATOR_LENGTH

    def add_node(self, node: OSMNode) -> None:
        """Add node and update map parameters."""
        if node.id_ in self.nodes:
            if node != self.nodes[node.id_]:
                raise NotWellFormedOSMDataException(
                    f"Node with duplicate id {node.id_}."
                )
            return
        self.nodes[node.id_] = node
        if node.user:
            self.authors.add(node.user)
        if node.tags.get("level"):
            self.levels.union(parse_levels(node.tags["level"]))
        self.time.update(node.timestamp)

        if not self.boundary_box:
            self.boundary_box = node.get_boundary_box()
        self.boundary_box.update(node.coordinates)

    def add_way(self, way: OSMWay) -> None:
        """Add way and update map parameters."""
        if way.id_ in self.ways:
            if way != self.ways[way.id_]:
                raise NotWellFormedOSMDataException(
                    f"Way with duplicate id {way.id_}."
                )
            return
        self.ways[way.id_] = way
        if way.user:
            self.authors.add(way.user)
        if way.tags.get("level"):
            self.levels.union(parse_levels(way.tags["level"]))
        if way.timestamp:
            self.time.update(way.timestamp)

    def add_relation(self, relation: OSMRelation) -> None:
        """Add relation and update map parameters."""
        if relation.id_ in self.relations:
            if relation != self.relations[relation.id_]:
                raise NotWellFormedOSMDataException(
                    f"Relation with duplicate id {relation.id_}."
                )
            return
        self.relations[relation.id_] = relation

    def parse_overpass(self, file_name: Path) -> None:
        """
        Parse JSON structure extracted from Overpass API.

        See https://wiki.openstreetmap.org/wiki/Overpass_API
        """
        with file_name.open(encoding="utf-8") as input_file:
            structure = json.load(input_file)

        node_map: dict[int, OSMNode] = {}
        way_map: dict[int, OSMWay] = {}

        for element in structure["elements"]:
            if element["type"] == "node":
                node = OSMNode.parse_from_structure(element)
                node_map[node.id_] = node
                self.add_node(node)
                if not self.view_box:
                    self.view_box = BoundaryBox(
                        node.coordinates[1],
                        node.coordinates[0],
                        node.coordinates[1],
                        node.coordinates[0],
                    )
                self.view_box.update(node.coordinates)

        for element in structure["elements"]:
            if element["type"] == "way":
                way = OSMWay.parse_from_structure(element, node_map)
                way_map[way.id_] = way
                self.add_way(way)

        for element in structure["elements"]:
            if element["type"] == "relation":
                relation = OSMRelation.parse_from_structure(element)
                self.add_relation(relation)

    def parse_osm_file(self, file_name: Path) -> None:
        """
        Parse OSM XML file.

        See https://wiki.openstreetmap.org/wiki/OSM_XML

        :param file_name: input XML file
        :return: parsed map
        """
        self.parse_osm(ElementTree.parse(file_name).getroot())

    def parse_osm_text(self, text: str) -> None:
        """
        Parse OSM XML data from text representation.

        :param text: XML text representation
        :return: parsed map
        """
        self.parse_osm(ElementTree.fromstring(text))

    def parse_osm(
        self,
        root: Element,
        parse_nodes: bool = True,
        parse_ways: bool = True,
        parse_relations: bool = True,
    ) -> None:
        """
        Parse OSM XML data.

        :param root: top element of XML data
        :param parse_nodes: whether nodes should be parsed
        :param parse_ways: whether ways should be parsed
        :param parse_relations: whether relations should be parsed
        """
        for element in root:
            if element.tag == "bounds":
                self.parse_bounds(element)
            elif element.tag == "object":
                self.parse_object(element)
            elif element.tag == "node" and parse_nodes:
                node = OSMNode.from_xml_structure(element)
                self.add_node(node)
            elif element.tag == "way" and parse_ways:
                self.add_way(OSMWay.from_xml_structure(element, self.nodes))
            elif element.tag == "relation" and parse_relations:
                self.add_relation(OSMRelation.from_xml_structure(element))

    def parse_bounds(self, element: Element) -> None:
        """Parse view box from XML element."""
        attributes = element.attrib
        boundary_box: BoundaryBox = BoundaryBox(
            float(attributes["minlon"]),
            float(attributes["minlat"]),
            float(attributes["maxlon"]),
            float(attributes["maxlat"]),
        )
        if self.view_box:
            self.view_box.combine(boundary_box)
        else:
            self.view_box = boundary_box

    def parse_object(self, element: Element) -> None:
        """Parse astronomical object properties from XML element."""
        self.equator_length = float(element.get("equator"))
