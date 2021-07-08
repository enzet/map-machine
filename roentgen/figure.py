from typing import Any, Dict, List, Optional

import numpy as np

from roentgen.flinger import Flinger
from roentgen.osm_reader import OSMNode, Tagged
from roentgen.road import Lane
from roentgen.scheme import LineStyle, RoadMatcher, Scheme


class Figure(Tagged):
    """
    Some figure on the map: way or area.
    """

    def __init__(
        self,
        tags: Dict[str, str],
        inners: List[List[OSMNode]],
        outers: List[List[OSMNode]],
    ):
        super().__init__()

        self.tags: Dict[str, str] = tags
        self.inners: List[List[OSMNode]] = []
        self.outers: List[List[OSMNode]] = []

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


class Building(Figure):
    """
    Building on the map.
    """

    def __init__(
        self,
        tags: Dict[str, str],
        inners: List[List[OSMNode]],
        outers: List[List[OSMNode]],
        flinger: Flinger,
        scheme: Scheme,
    ):
        super().__init__(tags, inners, outers)

        style: Dict[str, Any] = {
            "fill": scheme.get_color("building_color").hex,
            "stroke": scheme.get_color("building_border_color").hex,
        }
        self.line_style = LineStyle(style)
        self.parts = []

        for nodes in self.inners + self.outers:
            for i in range(len(nodes) - 1):
                flung_1: np.array = flinger.fling(nodes[i].coordinates)
                flung_2: np.array = flinger.fling(nodes[i + 1].coordinates)
                self.parts.append(Segment(flung_1, flung_2))

        self.parts = sorted(self.parts)

        self.height: float = 8.0
        self.min_height: float = 0.0

        levels: Optional[str] = self.get_float("building:levels")
        if levels:
            self.height = float(levels) * 2.5

        levels: Optional[str] = self.get_float("building:min_level")
        if levels:
            self.min_height = float(levels) * 2.5

        height: Optional[str] = self.get_length("height")
        if height:
            self.height = height

        height: Optional[str] = self.get_length("min_height")
        if height:
            self.min_height = height


class StyledFigure(Figure):
    """
    Figure with stroke and fill style.
    """

    def __init__(
        self,
        tags: Dict[str, str],
        inners: List[List[OSMNode]],
        outers: List[List[OSMNode]],
        line_style: LineStyle,
    ):
        super().__init__(tags, inners, outers)
        self.line_style = line_style


class Road(Figure):
    """
    Road or track on the map.
    """

    def __init__(
        self,
        tags: Dict[str, str],
        inners: List[List[OSMNode]],
        outers: List[List[OSMNode]],
        matcher: RoadMatcher,
    ):
        super().__init__(tags, inners, outers)
        self.matcher: RoadMatcher = matcher

        self.width: Optional[float] = None
        self.lanes: List[Lane] = []

        if "lanes" in tags:
            try:
                self.width = int(tags["lanes"]) * 3.7
                self.lanes = [Lane()] * int(tags["lanes"])
            except ValueError:
                pass

        if "lanes:forward" in tags:
            number = int(tags["lanes:forward"])
            [x.set_forward(True) for x in self.lanes[-number:]]
        if "lanes:backward" in tags:
            number = int(tags["lanes:backward"])
            [x.set_forward(False) for x in self.lanes[:number]]

        if "width" in tags:
            try:
                self.width = float(tags["width"])
            except ValueError:
                pass


class Segment:
    """
    Line segment.
    """

    def __init__(self, point_1: np.array, point_2: np.array):
        self.point_1 = point_1
        self.point_2 = point_2

        difference: np.array = point_2 - point_1
        vector: np.array = difference / np.linalg.norm(difference)
        self.angle: float = np.arccos(np.dot(vector, np.array((0, 1)))) / np.pi

    def __lt__(self, other: "Segment") -> bool:
        return (
            ((self.point_1 + self.point_2) / 2)[1]
            < ((other.point_1 + other.point_2) / 2)[1]
        )  # fmt: skip


def is_clockwise(polygon: List[OSMNode]) -> bool:
    """
    Return true if polygon nodes are in clockwise order.

    :param polygon: list of OpenStreetMap nodes
    """
    count: float = 0
    for index, node in enumerate(polygon):  # type: int, OSMNode
        next_index: int = 0 if index == len(polygon) - 1 else index + 1
        count += (polygon[next_index].coordinates[0] - node.coordinates[0]) * (
            polygon[next_index].coordinates[1] + node.coordinates[1]
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
