import numpy as np

from hashlib import sha256

from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from roentgen import ui
from roentgen.extract_icon import DEFAULT_SMALL_SHAPE_ID
from roentgen.flinger import Geo, GeoFlinger
from roentgen.osm_reader import OSMMember, OSMRelation, OSMWay
from roentgen.scheme import IconSet, Scheme


class Node:
    """
    Node in Röntgen terms.
    """
    def __init__(
            self, icon_set: IconSet, tags: Dict[str, str],
            point: (float, float), path: Optional[str],
            priority: int = 0, is_for_node: bool = True):
        self.icon_set: IconSet = icon_set
        self.tags = tags
        self.point = point
        self.path = path
        self.priority = priority
        self.layer = 0
        self.is_for_node = is_for_node


class Way:
    """
    Way in Röntgen terms.
    """
    def __init__(
            self, kind: str, nodes, path, style: Dict[str, Any],
            layer: float = 0.0, priority: float = 0, levels=None):
        self.kind = kind
        self.nodes = nodes
        self.path = path
        self.style: Dict[str, Any] = style
        self.layer = layer
        self.priority = priority
        self.levels = levels


def get_float(string):
    """
    Try to parse float from a string.
    """
    try:
        return float(string)
    except ValueError:
        return 0


def line_center(nodes, flinger: GeoFlinger):
    """
    Get geometric center of nodes set.
    """
    ma = [0, 0]
    mi = [10000, 10000]
    for node in nodes:
        flung = flinger.fling(Geo(node.lat, node.lon))
        if flung[0] > ma[0]:
            ma[0] = flung[0]
        if flung[1] > ma[1]:
            ma[1] = flung[1]
        if flung[0] < mi[0]:
            mi[0] = flung[0]
        if flung[1] < mi[1]:
            mi[1] = flung[1]
    return [(ma[0] + mi[0]) / 2.0, (ma[1] + mi[1]) / 2.0]


def get_user_color(text: str, seed: str):
    """
    Generate random color based on text.
    """
    if text == "":
        return "000000"
    rgb = sha256((seed + text).encode("utf-8")).hexdigest()[-6:]
    r = int(rgb[0:2], 16)
    g = int(rgb[2:4], 16)
    b = int(rgb[4:6], 16)
    c = (r + g + b) / 3.
    cc = 0
    r = r * (1 - cc) + c * cc
    g = g * (1 - cc) + c * cc
    b = b * (1 - cc) + c * cc
    h = hex(int(r))[2:] + hex(int(g))[2:] + hex(int(b))[2:]
    return "0" * (6 - len(h)) + h


def get_time_color(time):
    """
    Generate color based on time.
    """
    if not time:
        return "000000"
    time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")
    delta = (datetime.now() - time).total_seconds()
    time_color = hex(0xFF - min(0xFF, int(delta / 500000.)))[2:]
    i_time_color = hex(min(0xFF, int(delta / 500000.)))[2:]
    if len(time_color) == 1:
        time_color = "0" + time_color
    if len(i_time_color) == 1:
        i_time_color = "0" + i_time_color
    return time_color + "AA" + i_time_color


def glue(ways: List[OSMWay]):
    """
    Try to glue ways that share nodes.
    """
    result: List[List[int]] = []
    to_process: Set[OSMWay] = set()

    for way in ways:  # type: OSMWay
        if way.is_cycle():
            result.append(way.nodes)
        else:
            to_process.add(way)

    while to_process:
        way: OSMWay = to_process.pop()
        glued: Optional[OSMWay] = None

        for other_way in to_process:  # type: OSMWay
            glued = way.try_to_glue(other_way)
            if glued:
                break

        if glued:
            to_process.remove(other_way)
            if glued.is_cycle():
                result.append(glued.nodes)
            else:
                to_process.add(glued)
        else:
            result.append(way.nodes)

    return result


def get_path(nodes, shift, map_, flinger: GeoFlinger):
    """
    Construct SVG path from nodes.
    """
    path = ""
    prev_node = None
    for node_id in nodes:
        node = map_.node_map[node_id]
        flung = np.add(flinger.fling(Geo(node.lat, node.lon)), shift)
        path += ("L" if prev_node else "M") + f" {flung[0]},{flung[1]} "
        prev_node = map_.node_map[node_id]
    if nodes[0] == nodes[-1]:
        path += "Z"
    else:
        path = path[:-1]
    return path


class Constructor:
    """
    Röntgen node and way constructor.
    """
    def __init__(self, check_level, mode, seed, map_, flinger, scheme: Scheme):
        self.check_level = check_level
        self.mode = mode
        self.seed = seed
        self.map_ = map_
        self.flinger = flinger
        self.scheme: Scheme = scheme

        self.nodes: List[Node] = []
        self.ways: List[Way] = []

    def construct_ways(self):
        """
        Construct Röntgen ways.
        """
        for way_id in self.map_.way_map:  # type: int
            way: OSMWay = self.map_.way_map[way_id]
            if not self.check_level(way.tags):
                continue
            self.construct_way(way, way.tags, None)

    def construct_way(
            self, way: Optional[OSMWay], tags: Dict[str, Any],
            path: Optional[str]) -> None:
        """
        Way construction.

        :param way: OSM way.
        :param tags: way tag dictionary.
        :param path: way path (if there is no nodes).
        """
        layer: float = 0
        level: float = 0

        if "layer" in tags:
            layer = get_float(tags["layer"])
        if "level" in tags:
            try:
                levels = list(map(lambda x: float(x), tags["level"].split(";")))
                level = sum(levels) / len(levels)
            except ValueError:
                pass

        layer = 100 * level + 0.01 * layer

        nodes = None

        center_point = None

        if way:
            center_point = line_center(
                map(lambda x: self.map_.node_map[x], way.nodes), self.flinger)
            nodes = way.nodes

        if self.mode == "user-coloring":
            if not way:
                return
            user_color = get_user_color(way.user, self.seed)
            self.ways.append(
                Way("way", nodes, path,
                    {"fill": "none", "stroke": "#" + user_color,
                     "stroke-width": 1}))
            return

        if self.mode == "time":
            if not way:
                return
            time_color = get_time_color(way.timestamp)
            self.ways.append(
                Way("way", nodes, path,
                    {"fill": "none", "stroke": "#" + time_color,
                     "stroke-width": 1}))
            return

        if not tags:
            return

        appended = False
        kind: str = "way"
        levels = None

        if "building" in tags:
            kind = "building"
        if "building:levels" in tags:
            levels = float(tags["building:levels"])

        for element in self.scheme.ways:  # type: Dict[str, Any]
            matched: bool = True
            for config_tag_key in element["tags"]:  # type: str
                matcher = element["tags"][config_tag_key]
                if config_tag_key not in tags or \
                        (matcher != "*" and
                         tags[config_tag_key] != matcher and
                         tags[config_tag_key] not in matcher):
                    matched = False
                    break
            if "no_tags" in element:
                for config_tag_key in element["no_tags"]:  # type: str
                    if config_tag_key in tags and \
                            tags[config_tag_key] == \
                            element["no_tags"][config_tag_key]:
                        matched = False
                        break
            if matched:
                style: Dict[str, Any] = {"fill": "none"}
                if "layer" in element:
                    layer += element["layer"]
                for key in element:  # type: str
                    if key not in ["tags", "no_tags", "layer", "level", "icon"]:
                        value = element[key]
                        if isinstance(value, str) and value.endswith("_color"):
                            value = self.scheme.get_color(value)
                        style[key] = value
                self.ways.append(
                    Way(kind, nodes, path, style, layer, 50, levels))
                if center_point and way.is_cycle() or \
                        "area" in tags and tags["area"]:
                    icon_set: IconSet = self.scheme.get_icon(tags)
                    self.nodes.append(Node(
                        icon_set, tags, center_point, path, is_for_node=False))
                appended = True

        """
        if not appended:
            style: Dict[str, Any] = {
                "fill": "none", "stroke": "#FF0000", "stroke-width": 1}
            self.ways.append(Way(kind, nodes, path, style, layer, 50, levels))
            if center_point and way.is_cycle() or \
                    "area" in tags and tags["area"]:
                icon_set: IconSet = self.scheme.get_icon(tags)
                self.nodes.append(Node(
                    icon_set, tags, center_point, path, is_for_node=False))
        """

    def construct_relations(self) -> None:
        """
        Construct Röntgen ways from OSM relations.
        """
        for relation_id in self.map_.relation_map:
            relation: OSMRelation = self.map_.relation_map[relation_id]
            tags = relation.tags
            if not self.check_level(tags):
                continue
            if "type" in tags and tags["type"] == "multipolygon":
                inners, outers = [], []
                for member in relation.members:  # type: OSMMember
                    if member.type_ == "way":
                        if member.role == "inner":
                            if member.ref in self.map_.way_map:
                                inners.append(self.map_.way_map[member.ref])
                        elif member.role == "outer":
                            if member.ref in self.map_.way_map:
                                outers.append(self.map_.way_map[member.ref])
                p = ""
                inners_path = glue(inners)
                outers_path = glue(outers)
                for nodes in outers_path:
                    path = get_path(nodes, [0, 0], self.map_, self.flinger)
                    p += path + " "
                for nodes in inners_path:
                    nodes.reverse()
                    path = get_path(nodes, [0, 0], self.map_, self.flinger)
                    p += path + " "
                self.construct_way(None, tags, p)

    def construct_nodes(self) -> None:
        """
        Draw nodes.
        """
        print("Draw nodes...")

        start_time = datetime.now()

        node_number: int = 0

        s = sorted(
            self.map_.node_map.keys(), key=lambda x: -self.map_.node_map[x].lat)

        for node_id in s:  # type: int
            node_number += 1
            ui.progress_bar(node_number, len(self.map_.node_map))
            node = self.map_.node_map[node_id]
            flung = self.flinger.fling(Geo(node.lat, node.lon))
            tags = node.tags

            if not self.check_level(tags):
                continue

            icon_set: IconSet = self.scheme.get_icon(tags)

            if self.mode in ["time", "user-coloring"]:
                if not tags:
                    continue
                icon_set.icons = [[DEFAULT_SMALL_SHAPE_ID]]
            if self.mode == "user-coloring":
                icon_set.color = get_user_color(node.user, self.seed)
            if self.mode == "time":
                icon_set.color = get_time_color(node.timestamp)

            self.nodes.append(Node(icon_set, tags, flung, None))

        ui.progress_bar(-1, len(self.map_.node_map))

        print("Nodes painted in " + str(datetime.now() - start_time) + ".")
