"""
Reading OpenStreetMap data from XML file.

Author: Sergey Vartanov
"""
from typing import Any, Dict

from roentgen import ui


class OSMNode:
    def __init__(self, id_: int = 0, lat: float = 0, lon: float = 0):
        self.id_ = id_
        self.lat = lat
        self.lon = lon
        self.tags = {}

        self.visible = None
        self.changeset = None
        self.timestamp = None
        self.user = None
        self.uid = None

    def parse_from_xml(self, text: str, is_full: bool = False):
        """
        Parse full node parameters using regular expressions: id, visible, version,
        etc. For faster parsing use parse_node().
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
    def __init__(self, id_: int = 0, nodes=None):
        self.id_ = id_
        self.nodes = [] if nodes is None else nodes
        self.tags = {}

        self.visible = None
        self.changeset = None
        self.user = None
        self.timestamp = None
        self.uid = None

    def parse_from_xml(self, text: str, is_full: bool = False):
        self.id_ = int(get_value("id", text))

        if is_full:
            self.visible = get_value("visible", text)
            self.changeset = get_value("changeset", text)
            self.timestamp = get_value("timestamp", text)
            self.user = get_value("user", text)
            self.uid = get_value("uid", text)

        return self

    def is_cycle(self) -> bool:
        return self.nodes[0] == self.nodes[-1]

    def try_to_glue(self, other: "OSMWay"):
        if self.nodes[0] == other.nodes[0]:
            return OSMWay(nodes=list(reversed(other.nodes[1:])) + self.nodes)
        elif self.nodes[0] == other.nodes[-1]:
            return OSMWay(nodes=other.nodes[:-1] + self.nodes)
        elif self.nodes[-1] == other.nodes[-1]:
            return OSMWay(nodes=self.nodes + list(reversed(other.nodes[:-1])))
        elif self.nodes[-1] == other.nodes[0]:
            return OSMWay(nodes=self.nodes + other.nodes[1:])

    def __repr__(self):
        return str(self.nodes)


class OSMRelation:
    def __init__(self, id_):
        self.id_ = id_
        self.tags = {}
        self.members = []


def get_value(key: str, text: str):
    if key + '="' in text:
        index: int = text.find(key + '="')
        value = text[index + len(key) + 2:text.find('"', index + len(key) + 4)]
        return value


def parse_relation(text) -> OSMRelation:
    """
    Just parse relation identifier.
    """
    id = text[text.find("id=\"") + 4:text.find('"', text.find("id=\"") + 6)]
    return OSMRelation(int(id))


def parse_member(text) -> Dict[str, Any]:
    """
    Parse member type, reference, and role.
    """
    type = get_value("type", text)
    ref = get_value("ref", text)
    role = get_value("role", text)
    return {'type': type, 'ref': int(ref), 'role': role}


class Map:
    def __init__(self, node_map, way_map, relation_map):
        self.node_map = node_map
        self.way_map = way_map
        self.relation_map = relation_map


class OSMReader:
    def __init__(self, file_name: str):
        self.file_name = file_name

    def parse_osm_file(
            self, parse_nodes: bool = True, parse_ways: bool = True,
            parse_relations: bool = True, full: bool = False) -> Map:

        map_ = self.parse_osm_file_fast(
            parse_nodes=parse_nodes, parse_ways=parse_ways,
            parse_relations=parse_relations, full=full)
        return map_

    def parse_osm_file_fast(self, parse_nodes=True, parse_ways=True,
            parse_relations=True, full=False) -> Map:
        node_map: Dict[int, OSMNode] = {}
        way_map: Dict[int, OSMWay] = {}
        relation_map: Dict[int, OSMRelation] = {}
        print('Line number counting for ' + self.file_name + '...')
        with open(self.file_name) as f:
            for lines_number, l in enumerate(f):
                pass
        print('Done.')
        print('Parsing OSM file ' + self.file_name + '...')
        input_file = open(self.file_name)
        line = input_file.readline()
        line_number = 0

        while line != '':
            line_number += 1
            ui.write_line(line_number, lines_number)

            # Node parsing.

            if line[:6] in [' <node', '\t<node'] or line[:7] == "  <node":
                if not parse_nodes:
                    if parse_ways or parse_relations:
                        continue
                    else:
                        break
                if line[-3] == '/':
                    node: OSMNode = OSMNode().parse_from_xml(line[7:-3], full)
                    node_map[node.id_] = node
                else:
                    element = OSMNode().parse_from_xml(line[7:-2], full)
            elif line in [' </node>\n', '\t</node>\n', "  </node>\n"]:
                node_map[element.id_] = element

            # Way parsing.

            elif line[:5] in [' <way', '\t<way'] or line[:6] == "  <way":
                if not parse_ways:
                    if parse_relations:
                        continue
                    else:
                        break
                if line[-3] == '/':
                    way = OSMWay().parse_from_xml(line[6:-3], full)
                    way_map[way.id_] = way
                else:
                    element = OSMWay().parse_from_xml(line[6:-2], full)
            elif line in [' </way>\n', '\t</way>\n'] or line == "  </way>\n":
                way_map[element.id_] = element

            # Relation parsing.

            elif line[:10] in [' <relation', '\t<relation'] or \
                    line[:11] == "  <relation":
                if not parse_relations:
                    break
                if line[-3] == '/':
                    relation = parse_relation(line[11:-3])
                    relation_map[relation.id_] = relation
                else:
                    element = parse_relation(line[11:-2])
            elif line in [' </relation>\n', '\t</relation>\n'] or \
                    line == "  </relation>\n":
                relation_map[element.id_] = element

            # Elements parsing.

            elif line[:6] in ['  <tag', '\t\t<tag'] or line[:8] == "    <tag":
                k = get_value("k", line[7:-3])
                v = get_value("v", line[7:-3])
                element.tags[k] = v
            elif line[:5] in ['  <nd', '\t\t<nd'] or line[:7] == "    <nd":
                element.nodes.append(int(get_value("ref", line)))
            elif line[:9] in ['  <member', '\t\t<member'] or line[:11] == "    <member":
                member = parse_member(line[10:-3])
                element.members.append(member)
            line = input_file.readline()
        input_file.close()

        ui.write_line(-1, lines_number)  # Complete progress bar.

        return Map(node_map, way_map, relation_map)
