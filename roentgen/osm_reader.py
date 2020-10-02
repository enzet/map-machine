"""
Reading OpenStreetMap data from XML file.

Author: Sergey Vartanov (me@enzet.ru).
"""
import json

import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Set, Union, Any

from roentgen.ui import progress_bar
from roentgen.util import MinMax

OSM_TIME_PATTERN: str = "%Y-%m-%dT%H:%M:%SZ"


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

    def parse_from_xml(self, text: str, is_full: bool = False) -> "OSMNode":
        """
        Parse from XML node representation.

        :param text: XML node representation
        :param is_full: if false, parse only ID, latitude and longitude
        """
        self.id_ = int(get_value("id", text))
        self.coordinates = np.array((
            float(get_value("lat", text)), float(get_value("lon", text))))

        if is_full:
            self.visible = get_value("visible", text)
            self.changeset = get_value("changeset", text)
            self.timestamp = datetime.strptime(
                get_value("timestamp", text), OSM_TIME_PATTERN)
            self.user = get_value("user", text)
            self.uid = get_value("uid", text)

        return self

    def parse_from_structure(self, structure: Dict[str, Any]) -> "OSMNode":

        self.id_ = structure["id"]
        self.coordinates = np.array((structure["lat"], structure["lon"]))
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

    def parse_from_xml(self, text: str, is_full: bool = False) -> "OSMWay":
        """
        Parse from XML way representation.

        :param text: XML way representation
        :param is_full: if false, parse only ID
        """
        self.id_ = int(get_value("id", text))

        if is_full:
            self.visible = get_value("visible", text)
            self.changeset = get_value("changeset", text)
            self.timestamp = datetime.strptime(
                get_value("timestamp", text), OSM_TIME_PATTERN)
            self.user = get_value("user", text)
            self.uid = get_value("uid", text)

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

    def parse_from_xml(self, text: str) -> "OSMRelation":
        """
        Parse from XML relation representation.

        :param text: XML way representation
        """
        self.id_ = int(get_value("id", text))

        self.user = get_value("user", text)
        self.timestamp = datetime.strptime(
            get_value("timestamp", text), OSM_TIME_PATTERN)

        return self


class OSMMember:
    """
    Member of OpenStreetMap relation.
    """
    def __init__(self, text: str):
        self.type_: str = get_value("type", text)
        self.ref: int = int(get_value("ref", text))
        self.role: str = get_value("role", text)


def get_value(key: str, text: str):
    """
    Parse xml value from the tag in the format of key="value".
    """
    if key + '="' in text:
        start_index: int = text.find(key + '="') + 2
        end_index: int = start_index + len(key)
        value = text[end_index:text.find('"', end_index)]
        return value

    return None


class Map:
    """
    The whole OpenStreetMap information about nodes, ways, and relations.
    """
    def __init__(self):
        self.node_map: Dict[int, OSMNode] = {}
        self.way_map: Dict[int, OSMWay] = {}
        self.relation_map: Dict[int, OSMRelation] = {}

        self.authors: Set[str] = set()
        self.time: MinMax = MinMax()
        self.boundary_box: List[MinMax] = [MinMax(), MinMax()]

    def add_node(self, node: OSMNode):
        """
        Add node and update map parameters.
        """
        self.node_map[node.id_] = node
        if node.user:
            self.authors.add(node.user)
        self.time.update(node.timestamp)
        self.boundary_box[0].update(node.coordinates[0])
        self.boundary_box[1].update(node.coordinates[1])

    def add_way(self, way: OSMWay):
        """
        Add way and update map parameters.
        """
        self.way_map[way.id_] = way
        if way.user:
            self.authors.add(way.user)
        self.time.update(way.timestamp)

    def add_relation(self, relation: OSMRelation):
        """
        Add relation and update map parameters.
        """
        self.relation_map[relation.id_] = relation


class OverpassReader:
    def __init__(self):
        self.map_ = Map()

    def parse_json_file(self, file_name: str):
        with open(file_name) as input_file:
            structure = json.load(input_file)

        for element in structure["elements"]:
            if element["type"] == "node":
                node = OSMNode().parse_from_structure(element)
                self.map_.add_node(node)


class OSMReader:
    """
    OSM XML representation reader.
    """
    def __init__(self):
        self.map_ = Map()

    def parse_osm_file(
            self, file_name: str, parse_nodes: bool = True,
            parse_ways: bool = True, parse_relations: bool = True,
            full: bool = False) -> Map:
        """
        Parse OSM XML representation.

        :param file_name input OSM XML file name
        """
        with open(file_name) as input_file:
            lines_number: int = sum(1 for _ in input_file)

        print(f"Parsing OSM file {file_name}...")
        line_number: int = 0

        element: Optional[Union[OSMNode, OSMWay, OSMRelation]] = None

        with open(file_name) as input_file:
            for line in input_file.readlines():  # type: str

                line = line.strip()

                line_number += 1
                progress_bar(line_number, lines_number, text="Parsing")

                # Node parsing.

                if line.startswith("<node"):
                    if not parse_nodes:
                        if parse_ways or parse_relations:
                            continue
                        break
                    if line[-2] == "/":
                        node: OSMNode = OSMNode().parse_from_xml(line, full)
                        self.map_.add_node(node)
                    else:
                        element = OSMNode().parse_from_xml(line, full)
                elif line == "</node>":
                    self.map_.add_node(element)

                # Way parsing.

                elif line.startswith("<way"):
                    if not parse_ways:
                        if parse_relations:
                            continue
                        break
                    if line[-2] == "/":
                        way = OSMWay().parse_from_xml(line, full)
                        self.map_.add_way(way)
                    else:
                        element = OSMWay().parse_from_xml(line, full)
                elif line == "</way>":
                    self.map_.add_way(element)

                # Relation parsing.

                elif line.startswith("<relation"):
                    if not parse_relations:
                        break
                    if line[-2] == "/":
                        relation = OSMRelation().parse_from_xml(line)
                        self.map_.add_relation(relation)
                    else:
                        element = OSMRelation().parse_from_xml(line)
                elif line == "</relation>":
                    self.map_.add_relation(element)

                # Elements parsing.

                elif line.startswith("<tag"):
                    key: str = get_value("k", line)
                    value = get_value("v", line)
                    element.tags[key] = value
                elif line.startswith("<nd"):
                    element.nodes.append(
                        self.map_.node_map[int(get_value("ref", line))])
                elif line.startswith("<member"):
                    element.members.append(OSMMember(line))

        progress_bar(-1, lines_number, text="Parsing")

        return self.map_
