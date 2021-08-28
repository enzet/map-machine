"""
Figures displayed on the map.
"""
from typing import Any, Iterator, Optional

import numpy as np
from colour import Color
from svgwrite import Drawing
from svgwrite.container import Group
from svgwrite.path import Path

from roentgen.direction import DirectionSet, Sector
from roentgen.drawing import PathCommands
from roentgen.flinger import Flinger
from roentgen.osm_reader import OSMNode, Tagged
from roentgen.road import Lane
from roentgen.scheme import LineStyle, RoadMatcher, Scheme

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


class Figure(Tagged):
    """
    Some figure on the map: way or area.
    """

    def __init__(
        self,
        tags: dict[str, str],
        inners: list[list[OSMNode]],
        outers: list[list[OSMNode]],
    ) -> None:
        super().__init__()

        self.tags: dict[str, str] = tags
        self.inners: list[list[OSMNode]] = []
        self.outers: list[list[OSMNode]] = []

        for inner_nodes in inners:
            self.inners.append(make_clockwise(inner_nodes))
        for outer_nodes in outers:
            self.outers.append(make_counter_clockwise(outer_nodes))

    def get_path(
        self, flinger: Flinger, shift: np.ndarray = np.array((0, 0))
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
        tags: dict[str, str],
        inners: list[list[OSMNode]],
        outers: list[list[OSMNode]],
        flinger: Flinger,
        scheme: Scheme,
    ) -> None:
        super().__init__(tags, inners, outers)

        style: dict[str, Any] = {
            "fill": scheme.get_color("building_color").hex,
            "stroke": scheme.get_color("building_border_color").hex,
        }
        self.line_style: LineStyle = LineStyle(style)
        self.parts: list[Segment] = []

        for nodes in self.inners + self.outers:
            for i in range(len(nodes) - 1):
                flung_1: np.ndarray = flinger.fling(nodes[i].coordinates)
                flung_2: np.ndarray = flinger.fling(nodes[i + 1].coordinates)
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

        height: Optional[float] = self.get_length("height")
        if height:
            self.height = height

        height: Optional[float] = self.get_length("min_height")
        if height:
            self.min_height = height

    def draw(self, svg: Drawing, flinger: Flinger) -> None:
        """Draw simple building shape."""
        path: Path = Path(d=self.get_path(flinger))
        path.update(self.line_style.style)
        path.update({"stroke-linejoin": "round"})
        svg.add(path)

    def draw_shade(self, building_shade: Group, flinger: Flinger) -> None:
        """Draw shade casted by the building."""
        scale: float = flinger.get_scale() / 3.0
        shift_1: np.ndarray = np.array((scale * self.min_height, 0))
        shift_2: np.ndarray = np.array((scale * self.height, 0))
        commands: str = self.get_path(flinger, shift_1)
        path: Path = Path(
            d=commands, fill="#000000", stroke="#000000", stroke_width=1
        )
        building_shade.add(path)
        for nodes in self.inners + self.outers:
            for i in range(len(nodes) - 1):
                flung_1 = flinger.fling(nodes[i].coordinates)
                flung_2 = flinger.fling(nodes[i + 1].coordinates)
                command: PathCommands = [
                    "M",
                    np.add(flung_1, shift_1),
                    "L",
                    np.add(flung_2, shift_1),
                    np.add(flung_2, shift_2),
                    np.add(flung_1, shift_2),
                    "Z",
                ]
                path: Path = Path(
                    command, fill="#000000", stroke="#000000", stroke_width=1
                )
                building_shade.add(path)

    def draw_walls(
        self, svg: Drawing, height: float, previous_height: float, scale: float
    ) -> None:
        """Draw building walls."""
        shift_1: np.ndarray = np.array((0, -previous_height * scale))
        shift_2: np.ndarray = np.array((0, -height * scale))
        for segment in self.parts:
            fill: Color
            if height == 2:
                fill = Color("#AAAAAA")
            elif height == 4:
                fill = Color("#C3C3C3")
            else:
                color_part: float = 0.8 + segment.angle * 0.2
                fill = Color(rgb=(color_part, color_part, color_part))

            command = (
                "M",
                segment.point_1 + shift_1,
                "L",
                segment.point_2 + shift_1,
                segment.point_2 + shift_2,
                segment.point_1 + shift_2,
                segment.point_1 + shift_1,
                "Z",
            )
            path: Path = svg.path(
                d=command,
                fill=fill.hex,
                stroke=fill.hex,
                stroke_width=1,
                stroke_linejoin="round",
            )
            svg.add(path)

    def draw_roof(self, svg: Drawing, flinger: Flinger, scale: float) -> None:
        """Draw building roof."""
        path: Path = Path(
            d=self.get_path(flinger, np.array([0, -self.height * scale]))
        )
        path.update(self.line_style.style)
        path.update({"stroke-linejoin": "round"})
        svg.add(path)


class StyledFigure(Figure):
    """
    Figure with stroke and fill style.
    """

    def __init__(
        self,
        tags: dict[str, str],
        inners: list[list[OSMNode]],
        outers: list[list[OSMNode]],
        line_style: LineStyle,
    ) -> None:
        super().__init__(tags, inners, outers)
        self.line_style: LineStyle = line_style


class Road(Figure):
    """
    Road or track on the map.
    """

    def __init__(
        self,
        tags: dict[str, str],
        inners: list[list[OSMNode]],
        outers: list[list[OSMNode]],
        matcher: RoadMatcher,
    ) -> None:
        super().__init__(tags, inners, outers)
        self.matcher: RoadMatcher = matcher

        self.width: Optional[float] = None
        self.lanes: list[Lane] = []

        if "lanes" in tags:
            try:
                self.width = int(tags["lanes"]) * 3.7
                self.lanes = [Lane()] * int(tags["lanes"])
            except ValueError:
                pass

        number: int
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


class Tree(Tagged):
    """
    Tree on the map.
    """

    def __init__(
        self, tags: dict[str, str], coordinates: np.ndarray, point: np.ndarray
    ) -> None:
        super().__init__(tags)
        self.coordinates: np.ndarray = coordinates
        self.point: np.ndarray = point

    def draw(self, svg: Drawing, flinger: Flinger, scheme: Scheme) -> None:
        """Draw crown and trunk."""
        scale: float = flinger.get_scale(self.coordinates)
        radius: float
        if "diameter_crown" in self.tags:
            radius = float(self.tags["diameter_crown"]) / 2.0
        else:
            radius = 2.0
        color: Color = scheme.get_color("evergreen_color")
        svg.add(svg.circle(self.point, radius * scale, fill=color, opacity=0.3))

        if "circumference" in self.tags:
            radius: float = float(self.tags["circumference"]) / 2.0 / np.pi
            svg.add(svg.circle(self.point, radius * scale, fill="#B89A74"))


class DirectionSector(Tagged):
    """
    Sector that represents direction.
    """

    def __init__(self, tags: dict[str, str], point: np.ndarray) -> None:
        super().__init__(tags)
        self.point: np.ndarray = point

    def draw(self, svg: Drawing, scheme: Scheme) -> None:
        """Draw gradient sector."""
        angle: Optional[float] = None
        is_revert_gradient: bool = False
        direction: str
        direction_radius: float
        direction_color: Color

        if self.get_tag("man_made") == "surveillance":
            direction = self.get_tag("camera:direction")
            if "camera:angle" in self.tags:
                angle = float(self.get_tag("camera:angle"))
            if "angle" in self.tags:
                angle = float(self.get_tag("angle"))
            direction_radius = 25
            direction_color = scheme.get_color("direction_camera_color")
        elif self.get_tag("traffic_sign") == "stop":
            direction = self.get_tag("direction")
            direction_radius = 25
            direction_color = Color("red")
        else:
            direction = self.get_tag("direction")
            direction_radius = 50
            direction_color = scheme.get_color("direction_view_color")
            is_revert_gradient = True

        if not direction:
            return

        point: np.ndarray = (self.point.astype(int)).astype(float)

        paths: Iterator[PathCommands]
        if angle is not None:
            paths = [Sector(direction, angle).draw(point, direction_radius)]
        else:
            paths = DirectionSet(direction).draw(point, direction_radius)

        for path in paths:
            radial_gradient = svg.radialGradient(
                center=point,
                r=direction_radius,
                gradientUnits="userSpaceOnUse",
            )
            gradient = svg.defs.add(radial_gradient)
            if is_revert_gradient:
                (
                    gradient
                    .add_stop_color(0, direction_color.hex, opacity=0)
                    .add_stop_color(1, direction_color.hex, opacity=0.7)
                )  # fmt: skip
            else:
                (
                    gradient
                    .add_stop_color(0, direction_color.hex, opacity=0.4)
                    .add_stop_color(1, direction_color.hex, opacity=0)
                )  # fmt: skip
            path_element: Path = svg.path(
                d=["M", point] + path + ["L", point, "Z"],
                fill=gradient.get_paint_server(),
            )
            svg.add(path_element)


class Segment:
    """
    Line segment.
    """

    def __init__(self, point_1: np.ndarray, point_2: np.ndarray) -> None:
        self.point_1: np.ndarray = point_1
        self.point_2: np.ndarray = point_2

        difference: np.ndarray = point_2 - point_1
        vector: np.ndarray = difference / np.linalg.norm(difference)
        self.angle: float = np.arccos(np.dot(vector, np.array((0, 1)))) / np.pi

    def __lt__(self, other: "Segment") -> bool:
        return (
            ((self.point_1 + self.point_2) / 2)[1]
            < ((other.point_1 + other.point_2) / 2)[1]
        )  # fmt: skip


def is_clockwise(polygon: list[OSMNode]) -> bool:
    """
    Return true if polygon nodes are in clockwise order.

    :param polygon: list of OpenStreetMap nodes
    """
    count: float = 0
    for index, node in enumerate(polygon):
        next_index: int = 0 if index == len(polygon) - 1 else index + 1
        count += (polygon[next_index].coordinates[0] - node.coordinates[0]) * (
            polygon[next_index].coordinates[1] + node.coordinates[1]
        )
    return count >= 0


def make_clockwise(polygon: list[OSMNode]) -> list[OSMNode]:
    """
    Make polygon nodes clockwise.

    :param polygon: list of OpenStreetMap nodes
    """
    return polygon if is_clockwise(polygon) else list(reversed(polygon))


def make_counter_clockwise(polygon: list[OSMNode]) -> list[OSMNode]:
    """
    Make polygon nodes counter-clockwise.

    :param polygon: list of OpenStreetMap nodes
    """
    return polygon if not is_clockwise(polygon) else list(reversed(polygon))


def get_path(nodes: list[OSMNode], shift: np.ndarray, flinger: Flinger) -> str:
    """Construct SVG path commands from nodes."""
    path: str = ""
    prev_node: Optional[OSMNode] = None
    for node in nodes:
        flung: np.ndarray = flinger.fling(node.coordinates) + shift
        path += ("L" if prev_node else "M") + f" {flung[0]},{flung[1]} "
        prev_node = node
    if nodes[0] == nodes[-1]:
        path += "Z"
    else:
        path = path[:-1]
    return path
