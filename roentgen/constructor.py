"""
Construct Röntgen nodes and ways.

Author: Sergey Vartanov (me@enzet.ru).
"""
import numpy as np

from colour import Color
from datetime import datetime
from hashlib import sha256
from typing import Any, Dict, List, Optional, Set

from roentgen import ui
from roentgen.extract_icon import DEFAULT_SMALL_SHAPE_ID
from roentgen.flinger import Flinger
from roentgen.osm_reader import Map, OSMMember, OSMRelation, OSMWay, OSMNode, Tagged
from roentgen.scheme import IconSet, Scheme
from roentgen.util import MinMax
from roentgen.color import get_gradient_color

DEBUG: bool = False
TIME_COLOR_SCALE: List[Color] = [
    Color("#581845"), Color("#900C3F"), Color("#C70039"), Color("#FF5733"),
    Color("#FFC300"), Color("#DAF7A6")]


def is_clockwise(polygon: List[OSMNode]) -> bool:
    """
    Are polygon nodes are in clockwise order.
    """
    count: float = 0
    for index in range(len(polygon)):  # type: int
        next_index: int = 0 if index == len(polygon) - 1 else index + 1
        count += (
                (polygon[next_index].position[0] - polygon[index].position[0]) *
                (polygon[next_index].position[1] + polygon[index].position[1]))
    return count >= 0


def make_clockwise(polygon: List[OSMNode]) -> List[OSMNode]:
    if is_clockwise(polygon):
        return polygon
    else:
        return list(reversed(polygon))


def make_counter_clockwise(polygon: List[OSMNode]) -> List[OSMNode]:
    if not is_clockwise(polygon):
        return polygon
    else:
        return list(reversed(polygon))


class Node(Tagged):
    """
    Node in Röntgen terms.
    """
    def __init__(
            self, icon_set: IconSet, tags: Dict[str, str],
            point: np.array, coordinates: np.array,
            priority: float = 0, is_for_node: bool = True):
        assert point is not None

        self.icon_set: IconSet = icon_set
        self.tags: Dict[str, str] = tags
        self.point: np.array = point
        self.coordinates: np.array = coordinates
        self.priority: float = priority
        self.layer: float = 0
        self.is_for_node: bool = is_for_node

    def get_tag(self, key: str):
        if key in self.tags:
            return self.tags[key]
        return None


class Way:
    """
    Way in Röntgen terms.
    """
    def __init__(
            self, inners, outers, style: Dict[str, Any],
            layer: float = 0.0, levels=None):
        self.inners = []
        self.outers = []
        self.style: Dict[str, Any] = style
        self.layer = layer
        self.levels = levels

        for inner_nodes in inners:
            self.inners.append(make_clockwise(inner_nodes))
        for outer_nodes in outers:
            self.outers.append(make_counter_clockwise(outer_nodes))

    def get_path(
            self, flinger: Flinger, shift: np.array = np.array((0, 0))) -> str:
        """
        Get SVG path commands.

        :param shift: shift vector
        """
        path: str = ""

        for outer_nodes in self.outers:
            path += get_path(outer_nodes, shift, flinger) + " "

        for inner_nodes in self.inners:
            path += get_path(inner_nodes, shift, flinger) + " "

        return path

class TextStruct:
    def __init__(
            self, text: str, fill: Color = Color("#444444"), size: float = 10):
        self.text = text
        self.fill = fill
        self.size = size


def line_center(nodes: List[OSMNode], flinger: Flinger) -> np.array:
    """
    Get geometric center of nodes set.

    :param nodes: node list
    :param flinger: flinger that remap geo positions
    """
    boundary = [MinMax(), MinMax()]

    for node in nodes:  # type: OSMNode
        boundary[0].update(node.position[0])
        boundary[1].update(node.position[1])
    center_coordinates = np.array((boundary[0].center(), boundary[1].center()))

    return flinger.fling(center_coordinates), center_coordinates


def get_user_color(text: str, seed: str) -> Color:
    """
    Generate random color based on text.
    """
    if text == "":
        return Color("black")
    return Color("#" + sha256((seed + text).encode("utf-8")).hexdigest()[-6:])


def get_time_color(time: Optional[datetime], boundaries: MinMax) -> Color:
    """
    Generate color based on time.
    """
    return get_gradient_color(time, boundaries, TIME_COLOR_SCALE)


def glue(ways: List[OSMWay]) -> List[List[OSMNode]]:
    """
    Try to glue ways that share nodes.

    :param ways: ways to glue
    """
    result: List[List[OSMNode]] = []
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


def get_path(nodes: List[OSMNode], shift: np.array, flinger: Flinger) -> str:
    """
    Construct SVG path from nodes.
    """
    path = ""
    prev_node = None
    for node in nodes:
        flung = flinger.fling(node.position) + shift
        path += ("L" if prev_node else "M") + f" {flung[0]},{flung[1]} "
        prev_node = node
    if nodes[0] == nodes[-1]:
        path += "Z"
    else:
        path = path[:-1]
    return path


class Constructor:
    """
    Röntgen node and way constructor.
    """
    def __init__(
            self, check_level, mode: str, seed: str, map_: Map,
            flinger: Flinger, scheme: Scheme):

        self.check_level = check_level
        self.mode: str = mode
        self.seed: str = seed
        self.map_: Map = map_
        self.flinger: Flinger = flinger
        self.scheme: Scheme = scheme

        self.nodes: List[Node] = []
        self.ways: List[Way] = []
        self.buildings: List[Way] = []

    def construct_ways(self):
        """
        Construct Röntgen ways.
        """
        way_number: int = 0
        for way_id in self.map_.way_map:  # type: int
            ui.progress_bar(
                way_number, len(self.map_.way_map),
                text="Constructing ways")
            way_number += 1
            way: OSMWay = self.map_.way_map[way_id]
            if not self.check_level(way.tags):
                continue
            self.construct_way(way, way.tags, [], [way.nodes])

        ui.progress_bar(-1, len(self.map_.way_map), text="Constructing ways")

    def construct_way(
            self, way: Optional[OSMWay], tags: Dict[str, Any],
            inners, outers) -> None:
        """
        Way construction.

        :param way: OSM way
        :param tags: way tag dictionary
        """
        layer: float = 0
        # level: float = 0
        #
        # if "layer" in tags:
        #     layer = get_float(tags["layer"])
        # if "level" in tags:
        #     try:
        #         levels = list(map(float, tags["level"].split(";")))
        #         level = sum(levels) / len(levels)
        #     except ValueError:
        #         pass

        # layer = 100 * level + 0.01 * layer

        nodes = None

        center_point, center_coordinates = None, None

        if way:
            center_point, center_coordinates = \
                line_center(way.nodes, self.flinger)
            nodes = way.nodes

        if self.mode == "user-coloring":
            if not way:
                return
            user_color = get_user_color(way.user, self.seed)
            self.ways.append(
                Way(inners, outers,
                    {"fill": "none", "stroke": user_color.hex,
                     "stroke-width": 1}))
            return

        if self.mode == "time":
            if not way:
                return
            time_color = get_time_color(way.timestamp, self.map_.time)
            self.ways.append(
                Way(inners, outers,
                    {"fill": "none", "stroke": time_color.hex,
                     "stroke-width": 1}))
            return

        if not tags:
            return

        appended: bool = False
        kind: str = "way"
        levels = None

        if "building" in tags:  # or "building:part" in tags:
            kind = "building"
        if "building:levels" in tags:
            try:
                levels = float(tags["building:levels"])
            except ValueError:
                levels = None

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
                    if (config_tag_key in tags and
                            tags[config_tag_key] ==
                            element["no_tags"][config_tag_key]):
                        matched = False
                        break
            if matched:
                style: Dict[str, Any] = {"fill": "none"}
                if "priority" in element:
                    layer = element["priority"]
                for key in element:  # type: str
                    if key not in ["tags", "no_tags", "priority", "level", "icon", "r", "r2"]:
                        value = element[key]
                        if isinstance(value, str) and value.endswith("_color"):
                            value = self.scheme.get_color(value)
                        style[key] = value
                if center_coordinates is not None:
                    if "r" in element:
                        style["stroke-width"] = \
                            element["r"] * \
                            self.flinger.get_scale(center_coordinates)
                    if "r2" in element:
                        style["stroke-width"] = \
                            element["r2"] * \
                            self.flinger.get_scale(center_coordinates) + 2
                w = Way(inners, outers, style, layer, levels)
                if kind == "way":
                    self.ways.append(w)
                elif kind == "building":
                    self.buildings.append(w)
                if center_point is not None and \
                        (way.is_cycle() and "area" in tags and tags["area"]):
                    icon_set: IconSet = self.scheme.get_icon(tags)
                    self.nodes.append(Node(
                        icon_set, tags, center_point, center_coordinates,
                        is_for_node=False))
                appended = True

        if not appended:
            if DEBUG:
                style: Dict[str, Any] = {
                    "fill": "none", "stroke": Color("red").hex,
                    "stroke-width": 1}
                self.ways.append(Way(
                    kind, inners, outers, style, layer, levels))
            if center_point is not None and (way.is_cycle() or
                    "area" in tags and tags["area"]):
                icon_set: IconSet = self.scheme.get_icon(tags)
                self.nodes.append(Node(
                    icon_set, tags, center_point, center_coordinates,
                    is_for_node=False))

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
                inner_ways: List[OSMWay] = []
                outer_ways: List[OSMWay] = []
                for member in relation.members:  # type: OSMMember
                    if member.type_ == "way":
                        if member.role == "inner":
                            if member.ref in self.map_.way_map:
                                inner_ways.append(self.map_.way_map[member.ref])
                        elif member.role == "outer":
                            if member.ref in self.map_.way_map:
                                outer_ways.append(self.map_.way_map[member.ref])
                inners_path: List[List[OSMNode]] = glue(inner_ways)
                outers_path: List[List[OSMNode]] = glue(outer_ways)
                self.construct_way(None, tags, inners_path, outers_path)

    def construct_nodes(self) -> None:
        """
        Draw nodes.
        """
        node_number: int = 0

        s = sorted(
            self.map_.node_map.keys(),
            key=lambda x: -self.map_.node_map[x].position[0])

        for node_id in s:  # type: int
            node_number += 1
            ui.progress_bar(
                node_number, len(self.map_.node_map),
                text="Constructing nodes")
            node: OSMNode = self.map_.node_map[node_id]
            flung = self.flinger.fling(node.position)
            tags = node.tags

            if not self.check_level(tags):
                continue

            icon_set: IconSet = self.scheme.get_icon(tags)

            if self.mode in ["time", "user-coloring"]:
                if not tags:
                    continue
                icon_set.icons = [[DEFAULT_SMALL_SHAPE_ID]]
                break
            if self.mode == "user-coloring":
                icon_set.color = get_user_color(node.user, self.seed)
            if self.mode == "time":
                icon_set.color = get_time_color(node.timestamp)

            self.nodes.append(Node(icon_set, tags, flung, node.position))

        ui.progress_bar(-1, len(self.map_.node_map), text="Constructing nodes")
