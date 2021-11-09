"""
Figures displayed on the map.
"""
from typing import Any, Iterator, Optional

import numpy as np
from colour import Color
from svgwrite import Drawing
from svgwrite.container import Group
from svgwrite.gradients import RadialGradient
from svgwrite.path import Path

from map_machine.drawing import PathCommands
from map_machine.feature.direction import DirectionSet, Sector
from map_machine.geometry.flinger import Flinger
from map_machine.osm.osm_reader import OSMNode, Tagged
from map_machine.scheme import LineStyle, Scheme

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

from map_machine.geometry.vector import Polyline

BUILDING_HEIGHT_SCALE: float = 2.5
BUILDING_MINIMAL_HEIGHT: float = 8.0


class Figure(Tagged):
    """Some figure on the map: way or area."""

    def __init__(
        self,
        tags: dict[str, str],
        inners: list[list[OSMNode]],
        outers: list[list[OSMNode]],
    ) -> None:
        super().__init__(tags)

        self.inners: list[list[OSMNode]] = list(map(make_clockwise, inners))
        self.outers: list[list[OSMNode]] = list(
            map(make_counter_clockwise, outers)
        )

    def get_path(
        self, flinger: Flinger, offset: np.ndarray = np.array((0, 0))
    ) -> str:
        """
        Get SVG path commands.

        :param flinger: converter for geo coordinates
        :param offset: offset vector
        """
        path: str = ""

        for outer_nodes in self.outers:
            path += f"{get_path(outer_nodes, offset, flinger)} "

        for inner_nodes in self.inners:
            path += f"{get_path(inner_nodes, offset, flinger)} "

        return path


class Building(Figure):
    """Building on the map."""

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

        self.height: float = BUILDING_MINIMAL_HEIGHT
        self.min_height: float = 0.0

        levels: Optional[str] = self.get_float("building:levels")
        if levels:
            self.height = float(levels) * BUILDING_HEIGHT_SCALE

        levels: Optional[str] = self.get_float("building:min_level")
        if levels:
            self.min_height = float(levels) * BUILDING_HEIGHT_SCALE

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
    """Figure with stroke and fill style."""

    def __init__(
        self,
        tags: dict[str, str],
        inners: list[list[OSMNode]],
        outers: list[list[OSMNode]],
        line_style: LineStyle,
    ) -> None:
        super().__init__(tags, inners, outers)
        self.line_style: LineStyle = line_style


class Crater(Tagged):
    """Volcano or impact crater on the map."""

    def __init__(
        self, tags: dict[str, str], coordinates: np.ndarray, point: np.ndarray
    ) -> None:
        super().__init__(tags)
        self.coordinates: np.ndarray = coordinates
        self.point: np.ndarray = point

    def draw(self, svg: Drawing, flinger: Flinger) -> None:
        """Draw crater ridge."""
        scale: float = flinger.get_scale(self.coordinates)
        assert "diameter" in self.tags
        radius: float = float(self.tags["diameter"]) / 2.0
        radial_gradient = svg.radialGradient(
            center=self.point + np.array((0, radius * scale / 7)),
            r=radius * scale,
            gradientUnits="userSpaceOnUse",
        )
        color: Color = Color("#000000")
        gradient = svg.defs.add(radial_gradient)
        (
            gradient
            .add_stop_color(0, color.hex, opacity=0.2)
            .add_stop_color(0.7, color.hex, opacity=0.2)
            .add_stop_color(1, color.hex, opacity=1)
        )  # fmt: skip
        circle = svg.circle(
            self.point,
            radius * scale,
            fill=gradient.get_funciri(),
            opacity=0.2,
        )
        svg.add(circle)


class Tree(Tagged):
    """Tree on the map."""

    def __init__(
        self, tags: dict[str, str], coordinates: np.ndarray, point: np.ndarray
    ) -> None:
        super().__init__(tags)
        self.coordinates: np.ndarray = coordinates
        self.point: np.ndarray = point

    def draw(self, svg: Drawing, flinger: Flinger, scheme: Scheme) -> None:
        """Draw crown and trunk."""
        scale: float = flinger.get_scale(self.coordinates)
        diameter_crown: Optional[float] = self.get_float("diameter_crown")

        radius: float
        if diameter_crown is not None:
            radius = float(self.tags["diameter_crown"]) / 2.0
        else:
            radius = 2.0

        color: Color = scheme.get_color("evergreen_color")
        svg.add(svg.circle(self.point, radius * scale, fill=color, opacity=0.3))
        circumference: Optional[float] = self.get_float("circumference")

        if circumference is not None:
            radius: float = circumference / 2.0 / np.pi
            svg.add(svg.circle(self.point, radius * scale, fill="#B89A74"))


class DirectionSector(Tagged):
    """Sector that represents direction."""

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
            direction_radius = 50
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
            radial_gradient: RadialGradient = svg.radialGradient(
                center=point,
                r=direction_radius,
                gradientUnits="userSpaceOnUse",
            )
            gradient: RadialGradient = svg.defs.add(radial_gradient)

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
                fill=gradient.get_funciri(),
            )
            svg.add(path_element)


class Segment:
    """Closed line segment."""

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
    return Polyline(
        [flinger.fling(node.coordinates) + shift for node in nodes]
    ).get_path()
