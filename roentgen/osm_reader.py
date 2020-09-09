"""
Reading OpenStreetMap data from XML file.

Author: Sergey Vartanov
"""
from datetime import datetime
from typing import Dict, List, Optional

from roentgen import ui


class OSMNode:
    """
    OpenStreetMap node.

    See https://wiki.openstreetmap.org/wiki/Node
    """
    def __init__(self, id_: int = 0, lat: float = 0, lon: float = 0):
        self.id_: int = id_
        self.lat: float = lat
        self.lon: float = lon
        self.tags: Dict[str, str] = {}

        self.visible: Optional[str] = None
        self.changeset: Optional[str] = None
        self.timestamp: Optional[str] = None
        self.user: Optional[str] = None
        self.uid: Optional[str] = None

    def parse_from_xml(self, text: str, is_full: bool = False) -> "OSMNode":
        """
        Parse from XML node representation.

        :param text: XML node representation
        :param is_full: if false, parse only ID, latitude and longitude
        """
        self.id_ = int(get_value("id", text))
        self.lat = float(get_value("lat", text))
        self.lon = float(get_value("lon", text))

        if is_full:
            self.visible = get_value("visible", text)
            self.changeset = get_value("changeset", text)
            self.timestamp = get_value("timestamp", text)
            self.user = get_value("user", text)
            self.uid = get_value("uid", text)

        return self


class OSMWay:
    """
    OpenStreetMap way.

    See https://wiki.openstreetmap.org/wiki/Way
    """
    def __init__(self, id_: int = 0, nodes=None):
        self.id_: int = id_
        self.nodes: List[int] = [] if nodes is None else nodes
        self.tags: Dict[str, str] = {}

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
                get_value("timestamp", text), "%Y-%m-%dT%H:%M:%SZ")
            self.user = get_value("user", text)
            self.uid = get_value("uid", text)

        return self

    def is_cycle(self) -> bool:
        """
        Is way a cycle way or an area boundary.
        """
        return self.nodes[0] == self.nodes[-1]

    def try_to_glue(self, other: "OSMWay"):
        """
        Create new combined way if ways share endpoints.
        """
        if self.nodes[0] == other.nodes[0]:
            return OSMWay(nodes=list(reversed(other.nodes[1:])) + self.nodes)
        elif self.nodes[0] == other.nodes[-1]:
            return OSMWay(nodes=other.nodes[:-1] + self.nodes)
        elif self.nodes[-1] == other.nodes[-1]:
            return OSMWay(nodes=self.nodes + list(reversed(other.nodes[:-1])))
        elif self.nodes[-1] == other.nodes[0]:
            return OSMWay(nodes=self.nodes + other.nodes[1:])

    def __repr__(self):
        return f"Way <{self.id_}> {self.nodes}"


class OSMRelation:
    """
    OpenStreetMap relation.

    See https://wiki.openstreetmap.org/wiki/Relation
    """
    def __init__(self, id_: int = 0):
        self.id_: int = id_
        self.tags: Dict[str, str] = {}
        self.members: List["OSMMember"] = []

    def parse_from_xml(self, text: str) -> "OSMRelation":
        """
        Parse from XML relation representation.

        :param text: XML way representation
        """
        self.id_ = int(get_value("id", text))

        return self


class OSMMember:
    """
    Member of OpenStreetMap relation.
    """
    def __init__(self, text: str):
        self.type_ = get_value("type", text)
        self.ref = int(get_value("ref", text))
        self.role = get_value("role", text)


def get_value(key: str, text: str):
    """
    Parse xml value from the tag in the format of key="value".
    """
    if key + '="' in text:
        index: int = text.find(key + '="')
        value = text[index + len(key) + 2:text.find('"', index + len(key) + 4)]
        return value


class Map:
    """
    The whole OpenStreetMap information about nodes, ways, and relations.
    """
    def __init__(self):
        self.node_map: Dict[int, OSMNode] = {}
        self.way_map: Dict[int, OSMWay] = {}
        self.relation_map: Dict[int, OSMRelation] = {}


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
        """
        lines_number: int = sum(1 for _ in open(file_name))

        print(f"Parsing OSM file {file_name}...")
        input_file = open(file_name)
        line = input_file.readline()
        line_number = 0

        element = None

        while line != "":
            line_number += 1
            ui.progress_bar(line_number, lines_number)

            # Node parsing.

            if line[:6] in [" <node", "\t<node"] or line[:7] == "  <node":
                if not parse_nodes:
                    if parse_ways or parse_relations:
                        continue
                    break
                if line[-3] == "/":
                    node: OSMNode = OSMNode().parse_from_xml(line[7:-3], full)
                    self.map_.node_map[node.id_] = node
                else:
                    element = OSMNode().parse_from_xml(line[7:-2], full)
            elif line in [" </node>\n", "\t</node>\n", "  </node>\n"]:
                self.map_.node_map[element.id_] = element

            # Way parsing.

            elif line[:5] in [' <way', '\t<way'] or line[:6] == "  <way":
                if not parse_ways:
                    if parse_relations:
                        continue
                    break
                if line[-3] == '/':
                    way = OSMWay().parse_from_xml(line[6:-3], full)
                    self.map_.way_map[way.id_] = way
                else:
                    element = OSMWay().parse_from_xml(line[6:-2], full)
            elif line in [' </way>\n', '\t</way>\n'] or line == "  </way>\n":
                self.map_.way_map[element.id_] = element

            # Relation parsing.

            elif line[:10] in [" <relation", "\t<relation"] or \
                    line[:11] == "  <relation":
                if not parse_relations:
                    break
                if line[-3] == "/":
                    relation = OSMRelation().parse_from_xml(line[11:-3])
                    self.map_.relation_map[relation.id_] = relation
                else:
                    element = OSMRelation().parse_from_xml(line[11:-2])
            elif line in [" </relation>\n", "\t</relation>\n"] or \
                    line == "  </relation>\n":
                self.map_.relation_map[element.id_] = element

            # Elements parsing.

            elif line[:6] in ["  <tag", "\t\t<tag"] or line[:8] == "    <tag":
                k = get_value("k", line[7:-3])
                v = get_value("v", line[7:-3])
                element.tags[k] = v
            elif line[:5] in ["  <nd", "\t\t<nd"] or line[:7] == "    <nd":
                element.nodes.append(int(get_value("ref", line)))
            elif line[:9] in ["  <member", "\t\t<member"] or \
                    line[:11] == "    <member":
                element.members.append(OSMMember(line[10:-3]))
            line = input_file.readline()
        input_file.close()

        ui.progress_bar(-1, lines_number)  # Complete progress bar.

        return self.map_
