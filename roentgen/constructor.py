"""
Construct Röntgen nodes and ways.
"""
from collections import Counter
from datetime import datetime
from hashlib import sha256
from typing import Any, Dict, Iterator, List, Optional, Set

import numpy as np
from colour import Color

from roentgen import ui
from roentgen.color import get_gradient_color
from roentgen.flinger import Flinger
from roentgen.icon import (
    DEFAULT_SMALL_SHAPE_ID, Icon, IconSet, ShapeExtractor, ShapeSpecification
)
from roentgen.osm_reader import (
    Map, OSMMember, OSMNode, OSMRelation, OSMWay, Tagged
)
from roentgen.point import Point
from roentgen.scheme import DEFAULT_COLOR, LineStyle, Scheme
from roentgen.util import MinMax

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

DEBUG: bool = False
TIME_COLOR_SCALE: List[Color] = [
    Color("#581845"), Color("#900C3F"), Color("#C70039"), Color("#FF5733"),
    Color("#FFC300"), Color("#DAF7A6")
]


def is_clockwise(polygon: List[OSMNode]) -> bool:
    """
    Return true if polygon nodes are in clockwise order.

    :param polygon: list of OpenStreetMap nodes
    """
    count: float = 0
    for index, node in enumerate(polygon):  # type: int, OSMNode
        next_index: int = 0 if index == len(polygon) - 1 else index + 1
        count += (
            (polygon[next_index].coordinates[0] - node.coordinates[0]) *
            (polygon[next_index].coordinates[1] + node.coordinates[1])
        )
    return count >= 0


def make_clockwise(polygon: List[OSMNode]) -> List[OSMNode]:
    """
    Make polygon nodes clockwise.

    :param polygon: list of OpenStreetMap nodes
    """
    return polygon if is_clockwise(polygon) else list(reversed(polygon))


def make_counter_clockwise(polygon: List[OSMNode]) -> List[OSMNode]:
    """
    Make polygon nodes counter-clockwise.

    :param polygon: list of OpenStreetMap nodes
    """
    return polygon if not is_clockwise(polygon) else list(reversed(polygon))


class Figure(Tagged):
    """
    Some figure on the map: way or area.
    """

    def __init__(
        self, tags: Dict[str, str], inners: List[List[OSMNode]],
        outers: List[List[OSMNode]], line_style: LineStyle
    ):
        super().__init__()

        self.tags: Dict[str, str] = tags
        self.inners: List[List[OSMNode]] = []
        self.outers: List[List[OSMNode]] = []
        self.line_style = line_style

        for inner_nodes in inners:
            self.inners.append(make_clockwise(inner_nodes))
        for outer_nodes in outers:
            self.outers.append(make_counter_clockwise(outer_nodes))

    def get_path(
        self, flinger: Flinger, shift: np.array = np.array((0, 0))
    ) -> str:
        """
        Get SVG path commands.

        :param flinger: converter for geo coordinates
        :param shift: shift vector
        """
        path: str = ""

        for outer_nodes in self.outers:
            path += f"{get_path(outer_nodes, shift, flinger)} "

        for inner_nodes in self.inners:
            path += f"{get_path(inner_nodes, shift, flinger)} "

        return path


class Segment:
    """
    Line segment.
    """

    def __init__(self, point_1: np.array, point_2: np.array):
        self.point_1 = point_1
        self.point_2 = point_2

        difference: np.array = point_2 - point_1
        vector: np.array = difference / np.linalg.norm(difference)
        self.angle: float = (
            np.arccos(np.dot(vector, np.array((0, 1)))) / np.pi
        )

    def __lt__(self, other: "Segment") -> bool:
        return (
            ((self.point_1 + self.point_2) / 2)[1] <
            ((other.point_1 + other.point_2) / 2)[1]
        )


class Building(Figure):
    """
    Building on the map.
    """

    def __init__(
        self, tags: Dict[str, str], inners, outers, flinger: Flinger,
        line_style: LineStyle
    ):
        super().__init__(tags, inners, outers, line_style)

        self.parts = []

        for nodes in self.inners + self.outers:
            for i in range(len(nodes) - 1):
                flung_1: np.array = flinger.fling(nodes[i].coordinates)
                flung_2: np.array = flinger.fling(nodes[i + 1].coordinates)
                self.parts.append(Segment(flung_1, flung_2))

        self.parts = sorted(self.parts)

    def get_levels(self) -> float:
        """
        Get building level number.
        """
        try:
            return max(3.0, float(self.get_tag("building:levels")))
        except (ValueError, TypeError):
            return 3


def line_center(nodes: List[OSMNode], flinger: Flinger) -> np.array:
    """
    Get geometric center of nodes set.

    :param nodes: node list
    :param flinger: flinger that remap geo positions
    """
    boundary: List[MinMax] = [MinMax(), MinMax()]

    for node in nodes:  # type: OSMNode
        boundary[0].update(node.coordinates[0])
        boundary[1].update(node.coordinates[1])
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

    :param time: current element creation time
    :param boundaries: minimum and maximum element creation time on the map
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
        other_way: Optional[OSMWay] = None

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
    Construct SVG path commands from nodes.
    """
    path: str = ""
    prev_node: Optional[OSMNode] = None
    for node in nodes:  # type: OSMNode
        flung = flinger.fling(node.coordinates) + shift
        path += ("L" if prev_node else "M") + f" {flung[0]},{flung[1]} "
        prev_node = node
    if nodes[0] == nodes[-1]:
        path += "Z"
    else:
        path = path[:-1]
    return path


def is_cycle(nodes) -> bool:
    """
    Is way a cycle way or an area boundary.
    """
    return nodes[0] == nodes[-1]


class Constructor:
    """
    Röntgen node and way constructor.
    """

    def __init__(
        self, map_: Map, flinger: Flinger, scheme: Scheme,
        icon_extractor: ShapeExtractor, check_level=lambda x: True,
        mode: str = "normal", seed: str = ""
    ):
        self.check_level = check_level
        self.mode: str = mode
        self.seed: str = seed
        self.map_: Map = map_
        self.flinger: Flinger = flinger
        self.scheme: Scheme = scheme
        self.icon_extractor = icon_extractor

        self.points: List[Point] = []
        self.figures: List[Figure] = []
        self.buildings: List[Building] = []

        self.levels: Set[float] = {0.5, 1.0}

    def add_building(self, building: Building) -> None:
        """
        Add building and update levels.
        """
        self.buildings.append(building)
        self.levels.add(building.get_levels())

    def construct(self) -> None:
        """
        Construct nodes, ways, and relations.
        """
        self.construct_ways()
        self.construct_relations()
        self.construct_nodes()

    def construct_ways(self) -> None:
        """
        Construct Röntgen ways.
        """
        way_number: int = 0
        for way_id in self.map_.way_map:  # type: int
            ui.progress_bar(
                way_number, len(self.map_.way_map), step=10,
                text="Constructing ways")
            way_number += 1
            way: OSMWay = self.map_.way_map[way_id]
            if not self.check_level(way.tags):
                continue
            self.construct_line(way, [], [way.nodes])

        ui.progress_bar(-1, len(self.map_.way_map), text="Constructing ways")

    def construct_line(
        self, line: Optional[Tagged],
        inners: List[List[OSMNode]], outers: List[List[OSMNode]]
    ) -> None:
        """
        Way or relation construction.

        :param line: OpenStreetMap way or relation
        :param inners: list of polygons that compose inner boundary
        :param outers: list of polygons that compose outer boundary
        """
        assert len(outers) >= 1

        center_point, center_coordinates = (
            line_center(outers[0], self.flinger))

        if self.mode == "user-coloring":
            user_color = get_user_color(line.user, self.seed)
            self.figures.append(Figure(
                line.tags, inners, outers,
                LineStyle({
                    "fill": "none", "stroke": user_color.hex, "stroke-width": 1
                })
            ))
            return

        if self.mode == "time":
            time_color = get_time_color(line.timestamp, self.map_.time)
            self.figures.append(Figure(
                line.tags, inners, outers,
                LineStyle({
                    "fill": "none", "stroke": time_color.hex, "stroke-width": 1
                })
            ))
            return

        if not line.tags:
            return

        scale: float = self.flinger.get_scale(center_coordinates)

        line_styles: List[LineStyle] = self.scheme.get_style(line.tags, scale)

        for line_style in line_styles:  # type: LineStyle
            if "building" in line.tags:
                self.add_building(Building(
                    line.tags, inners, outers, self.flinger, line_style
                ))
            else:
                self.figures.append(
                    Figure(line.tags, inners, outers, line_style))
            if (
                line.get_tag("area") == "yes" or
                is_cycle(outers[0]) and line.get_tag("area") != "no" and
                self.scheme.is_area(line.tags)
            ):
                priority: int
                icon_set: IconSet
                icon_set, priority = self.scheme.get_icon(
                    self.icon_extractor, line.tags, for_="line"
                )
                labels = self.scheme.construct_text(line.tags, "all")

                self.points.append(Point(
                    icon_set, labels, line.tags, center_point,
                    center_coordinates, is_for_node=False, priority=priority
                ))

        if not line_styles:
            if DEBUG:
                style: Dict[str, Any] = {
                    "fill": "none", "stroke": Color("red").hex,
                    "stroke-width": 1}
                self.figures.append(Figure(
                    line.tags, inners, outers, LineStyle(style, 1000)))

            priority: int
            icon_set: IconSet
            icon_set, priority = self.scheme.get_icon(
                self.icon_extractor, line.tags
            )
            labels = self.scheme.construct_text(line.tags, "all")

            self.points.append(Point(
                icon_set, labels, line.tags, center_point, center_coordinates,
                is_for_node=False, priority=priority
            ))

    def construct_relations(self) -> None:
        """
        Construct Röntgen ways from OSM relations.
        """
        for relation_id in self.map_.relation_map:
            relation: OSMRelation = self.map_.relation_map[relation_id]
            tags = relation.tags
            if not self.check_level(tags):
                continue
            if "type" not in tags or tags["type"] != "multipolygon":
                continue
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
                    else:
                        print(f'Unknown member role "{member.role}".')
            if outer_ways:
                inners_path: List[List[OSMNode]] = glue(inner_ways)
                outers_path: List[List[OSMNode]] = glue(outer_ways)
                self.construct_line(relation, inners_path, outers_path)

    def construct_nodes(self) -> None:
        """
        Draw nodes.
        """
        node_number: int = 0

        sorted_node_ids: Iterator[int] = sorted(
            self.map_.node_map.keys(),
            key=lambda x: -self.map_.node_map[x].coordinates[0])

        missing_tags = Counter()

        for node_id in sorted_node_ids:  # type: int
            node_number += 1
            ui.progress_bar(
                node_number, len(self.map_.node_map),
                text="Constructing nodes")
            node: OSMNode = self.map_.node_map[node_id]
            flung = self.flinger.fling(node.coordinates)
            tags = node.tags

            if not self.check_level(tags):
                continue

            priority: int
            icon_set: IconSet
            draw_outline: bool = True

            if self.mode in ["time", "user-coloring"]:
                if not tags:
                    continue
                color = DEFAULT_COLOR
                if self.mode == "user-coloring":
                    color = get_user_color(node.user, self.seed)
                if self.mode == "time":
                    color = get_time_color(node.timestamp, self.map_.time)
                dot = self.icon_extractor.get_shape(DEFAULT_SMALL_SHAPE_ID)
                icon_set = IconSet(
                    Icon([ShapeSpecification(dot, color)]), [], set()
                )
                priority = 0
                draw_outline = False
                labels = []
            else:
                icon_set, priority = self.scheme.get_icon(
                    self.icon_extractor, tags
                )
                labels = self.scheme.construct_text(tags, "all")

            self.points.append(Point(
                icon_set, labels, tags, flung, node.coordinates,
                priority=priority, draw_outline=draw_outline
            ))

            missing_tags.update(
                f"{key}: {tags[key]}" for key in tags
                if key not in icon_set.processed)

        ui.progress_bar(-1, len(self.map_.node_map), text="Constructing nodes")
