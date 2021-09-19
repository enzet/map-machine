"""
WIP: road shape drawing.
"""
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np
import svgwrite
from colour import Color
from svgwrite import Drawing
from svgwrite.path import Path

from map_machine.drawing import PathCommands
from map_machine.flinger import Flinger
from map_machine.osm_reader import OSMNode, Tagged
from map_machine.scheme import RoadMatcher

from map_machine.vector import (
    Line,
    Polyline,
    compute_angle,
    norm,
    turn_by_angle,
)

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


@dataclass
class Lane:
    """
    Road lane specification.
    """

    width: Optional[float] = None  # Width in meters
    is_forward: Optional[bool] = None  # Whether lane is forward or backward
    min_speed: Optional[float] = None  # Minimal speed on the lane
    # "none", "merge_to_left", "slight_left", "slight_right"
    turn: Optional[str] = None
    change: Optional[str] = None  # "not_left", "not_right"
    destination: Optional[str] = None  # Lane destination

    def set_forward(self, is_forward: bool) -> None:
        """If true, lane is forward, otherwise it's backward."""
        self.is_forward = is_forward

    def get_width(self, scale: float) -> float:
        """Get lane width.  We use standard 3.7 m lane."""
        if self.width is None:
            return 3.7 * scale
        return self.width * scale


class RoadPart:
    """
    Line part of the road.
    """

    def __init__(
        self,
        point_1: np.ndarray,
        point_2: np.ndarray,
        lanes: list[Lane],
        scale: float,
    ) -> None:
        """
        :param point_1: start point of the road part
        :param point_2: end point of the road part
        :param lanes: lane specification
        """
        self.point_1: np.ndarray = point_1
        self.point_2: np.ndarray = point_2
        self.lanes: list[Lane] = lanes
        if lanes:
            self.width = sum(map(lambda x: x.get_width(scale), lanes))
        else:
            self.width = 1
        self.left_offset: float = self.width / 2
        self.right_offset: float = self.width / 2

        self.turned: np.ndarray = norm(
            turn_by_angle(self.point_2 - self.point_1, np.pi / 2)
        )
        self.right_vector: np.ndarray = self.turned * self.right_offset
        self.left_vector: np.ndarray = -self.turned * self.left_offset

        self.right_connection: Optional[np.ndarray] = None
        self.left_connection: Optional[np.ndarray] = None
        self.right_projection: Optional[np.ndarray] = None
        self.left_projection: Optional[np.ndarray] = None

        self.left_outer: Optional[np.ndarray] = None
        self.right_outer: Optional[np.ndarray] = None
        self.point_a: Optional[np.ndarray] = None
        self.point_middle: Optional[np.ndarray] = None

    def update(self) -> None:
        """Compute additional points."""
        if self.left_connection is not None:
            self.right_projection = (
                self.left_connection + self.right_vector - self.left_vector
            )
        if self.right_connection is not None:
            self.left_projection = (
                self.right_connection - self.right_vector + self.left_vector
            )
        if (
            self.left_connection is not None
            and self.right_connection is not None
        ):
            a = np.linalg.norm(self.right_connection - self.point_1)
            b = np.linalg.norm(self.right_projection - self.point_1)
            if a > b:
                self.right_outer = self.right_connection
                self.left_outer = self.left_projection
            else:
                self.right_outer = self.right_projection
                self.left_outer = self.left_connection
            self.point_middle = self.right_outer - self.right_vector

            max_: float = 100

            if np.linalg.norm(self.point_middle - self.point_1) > max_:
                self.point_a = self.point_1 + max_ * norm(
                    self.point_middle - self.point_1
                )
                self.right_outer = self.point_a + self.right_vector
                self.left_outer = self.point_a + self.left_vector
            else:
                self.point_a = self.point_middle

    def get_angle(self) -> float:
        """Get an angle between line and x axis."""
        return compute_angle(self.point_2 - self.point_1)

    def draw_normal(self, drawing: svgwrite.Drawing) -> None:
        """Draw some debug lines."""
        line: Path = drawing.path(
            ("M", self.point_1, "L", self.point_2),
            fill="none",
            stroke="#8888FF",
            stroke_width=self.width,
        )
        drawing.add(line)

    def draw_debug(self, drawing: svgwrite.Drawing) -> None:
        """Draw some debug lines."""
        line: Path = drawing.path(
            ("M", self.point_1, "L", self.point_2),
            fill="none",
            stroke="#000000",
        )
        drawing.add(line)
        line: Path = drawing.path(
            (
                "M", self.point_1 + self.right_vector,
                "L", self.point_2 + self.right_vector,
            ),
            fill="none",
            stroke="#FF0000",
            stroke_width=0.5,
        )  # fmt: skip
        drawing.add(line)
        line = drawing.path(
            (
                "M", self.point_1 + self.left_vector,
                "L", self.point_2 + self.left_vector,
            ),
            fill="none",
            stroke="#0000FF",
            stroke_width=0.5,
        )  # fmt: skip
        drawing.add(line)

        opacity: float = 0.4
        radius: float = 2

        if self.right_connection is not None:
            circle = drawing.circle(
                self.right_connection, 2.5, fill="#FF0000", opacity=opacity
            )
            drawing.add(circle)
        if self.left_connection is not None:
            circle = drawing.circle(
                self.left_connection, 2.5, fill="#0000FF", opacity=opacity
            )
            drawing.add(circle)

        if self.right_projection is not None:
            circle = drawing.circle(
                self.right_projection, 1.5, fill="#FF0000", opacity=opacity
            )
            drawing.add(circle)
        if self.left_projection is not None:
            circle = drawing.circle(
                self.left_projection, 1.5, fill="#0000FF", opacity=opacity
            )
            drawing.add(circle)

        if self.right_outer is not None:
            circle = drawing.circle(
                self.right_outer,
                3.5,
                stroke_width=0.5,
                fill="none",
                stroke="#FF0000",
                opacity=opacity,
            )
            drawing.add(circle)
        if self.left_outer is not None:
            circle = drawing.circle(
                self.left_outer,
                3.5,
                stroke_width=0.5,
                fill="none",
                stroke="#0000FF",
                opacity=opacity,
            )
            drawing.add(circle)

        if self.point_a is not None:
            circle = drawing.circle(self.point_a, radius, fill="#000000")
            drawing.add(circle)

        # self.draw_entrance(drawing, True)

    def draw(self, drawing: svgwrite.Drawing) -> None:
        """Draw road part."""
        if self.left_connection is not None:
            path_commands = [
                "M", self.point_2 + self.right_vector,
                "L", self.point_2 + self.left_vector,
                "L", self.left_connection,
                "L", self.right_connection,
                "Z",
            ]  # fmt: skip
            drawing.add(drawing.path(path_commands, fill="#CCCCCC"))

    def draw_entrance(
        self, drawing: svgwrite.Drawing, is_debug: bool = False
    ) -> None:
        """Draw intersection entrance part."""
        if (
            self.left_connection is not None
            and self.right_connection is not None
        ):
            path_commands = [
                "M", self.right_projection,
                "L", self.right_connection,
                "L", self.left_projection,
                "L", self.left_connection,
                "Z",
            ]  # fmt: skip
            if is_debug:
                path = drawing.path(
                    path_commands,
                    fill="none",
                    stroke="#880088",
                    stroke_width=0.5,
                )
                drawing.add(path)
            else:
                drawing.add(drawing.path(path_commands, fill="#88FF88"))

    def draw_lanes(self, drawing: svgwrite.Drawing, scale: float) -> None:
        """Draw lane delimiters."""
        for lane in self.lanes:
            shift = self.right_vector - self.turned * lane.get_width(scale)
            path = drawing.path(
                ["M", self.point_middle + shift, "L", self.point_2 + shift],
                fill="none",
                stroke="#FFFFFF",
                stroke_width=2,
                stroke_dasharray="7,7",
            )
            drawing.add(path)


class Intersection:
    """
    An intersection of the roads, that is described by its parts.  All first
    points of the road parts should be the same.
    """

    def __init__(self, parts: list[RoadPart]) -> None:
        self.parts: list[RoadPart] = sorted(parts, key=lambda x: x.get_angle())

        for index in range(len(self.parts)):
            next_index: int = 0 if index == len(self.parts) - 1 else index + 1
            part_1: RoadPart = self.parts[index]
            part_2: RoadPart = self.parts[next_index]
            line_1: Line = Line(
                part_1.point_1 + part_1.right_vector,
                part_1.point_2 + part_1.right_vector,
            )
            line_2: Line = Line(
                part_2.point_1 + part_2.left_vector,
                part_2.point_2 + part_2.left_vector,
            )
            intersection: np.ndarray = line_1.get_intersection_point(line_2)
            # if np.linalg.norm(intersection - part_1.point_2) < 300:
            part_1.right_connection = intersection
            part_2.left_connection = intersection
            part_1.update()
            part_2.update()

        for index in range(len(self.parts)):
            next_index: int = 0 if index == len(self.parts) - 1 else index + 1
            part_1: RoadPart = self.parts[index]
            part_2: RoadPart = self.parts[next_index]
            part_1.update()
            part_2.update()

            if (
                part_1.right_connection is None
                and part_2.left_connection is None
            ):
                part_1.left_connection = part_1.right_projection
                part_2.right_connection = part_2.left_projection
                part_1.left_outer = part_1.right_projection
                part_2.right_outer = part_2.left_projection

            part_1.update()
            part_2.update()

    def draw(self, drawing: svgwrite.Drawing, is_debug: bool = False) -> None:
        """Draw all road parts and intersection."""
        inner_commands = ["M"]
        for part in self.parts:
            inner_commands += [part.left_connection, "L"]
        inner_commands[-1] = "Z"

        outer_commands = ["M"]
        for part in self.parts:
            outer_commands += [part.left_connection, "L"]
            outer_commands += [part.left_outer, "L"]
            outer_commands += [part.right_outer, "L"]
        outer_commands[-1] = "Z"

        # for part in self.parts:
        #     part.draw_normal(drawing)

        if is_debug:
            drawing.add(
                drawing.path(outer_commands, fill="#0000FF", opacity=0.2)
            )
            drawing.add(
                drawing.path(inner_commands, fill="#FF0000", opacity=0.2)
            )

        for part in self.parts:
            if is_debug:
                part.draw_debug(drawing)
            else:
                part.draw_entrance(drawing)
        if not is_debug:
            # for part in self.parts:
            #     part.draw_lanes(drawing, scale)
            drawing.add(drawing.path(inner_commands, fill="#FF8888"))


class Road(Tagged):
    """
    Road or track on the map.
    """

    def __init__(
        self,
        tags: dict[str, str],
        nodes: list[OSMNode],
        matcher: RoadMatcher,
        flinger: Flinger,
    ) -> None:
        super().__init__(tags)
        self.nodes: list[OSMNode] = nodes
        self.matcher: RoadMatcher = matcher

        self.line: Polyline = Polyline(
            [flinger.fling(x.coordinates) for x in self.nodes]
        )
        self.width: Optional[float] = matcher.default_width
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

        self.layer: float = 0
        if "layer" in tags:
            self.layer = float(tags["layer"])

    def draw(
        self,
        svg: Drawing,
        flinger: Flinger,
        color: Color,
        extra_width: float = 0,
    ) -> None:
        """Draw road as simple SVG path."""
        width: float
        if self.width is not None:
            width = self.width
        else:
            width = self.matcher.default_width
        if extra_width and self.tags.get("bridge") == "yes":
            color = Color("#666666")
        scale: float = flinger.get_scale(self.nodes[0].coordinates)
        path_commands: str = self.line.get_path()
        path: Path = Path(d=path_commands)
        style: dict[str, Any] = {
            "fill": "none",
            "stroke": color.hex,
            "stroke-linecap": "butt",
            "stroke-linejoin": "round",
            "stroke-width": scale * width + extra_width,
        }
        path.update(style)
        svg.add(path)

    def draw_lanes(self, svg: Drawing, flinger: Flinger, color: Color) -> None:
        """Draw lane separators."""
        scale: float = flinger.get_scale(self.nodes[0].coordinates)
        if len(self.lanes) < 2:
            return
        for index in range(1, len(self.lanes)):
            parallel_offset: float = scale * (
                -self.width / 2 + index * self.width / len(self.lanes)
            )
            path: Path = Path(d=self.line.get_path(parallel_offset))
            style: dict[str, Any] = {
                "fill": "none",
                "stroke": color.hex,
                "stroke-linejoin": "round",
                "stroke-width": 1,
                "opacity": 0.5,
            }
            path.update(style)
            svg.add(path)


def get_curve_points(
    road: Road, scale: float, center: np.ndarray, road_end: np.ndarray
) -> list[np.ndarray]:
    """
    :param road: road segment
    :param scale: current zoom scale
    :param center: road intersection point
    :param road_end: end point of the road segment
    """
    width: float = road.width / 2.0 * scale

    direction: np.ndarray = (road_end - center) / np.linalg.norm(
        road_end - center
    )
    left: np.ndarray = turn_by_angle(direction, np.pi / 2.0) * width
    right: np.ndarray = turn_by_angle(direction, -np.pi / 2.0) * width

    return [road_end + left, center + left, center + right, road_end + right]


class Connector:
    """
    Two roads connection.
    """

    def __init__(
        self,
        road_1: Road,
        index_1: int,
        road_2: Road,
        index_2: int,
        flinger: Flinger,
        scale: float,
    ) -> None:
        self.road_1: Road = road_1
        self.road_2: Road = road_2

        self.index_1: int = index_1
        self.index_2: int = index_2

        self.layer: float = min(road_1.layer, road_2.layer)

    def draw(self, svg: Drawing) -> None:
        """Draw connection fill."""
        raise NotImplementedError

    def draw_border(self, svg: Drawing) -> None:
        """Draw connection outline."""
        raise NotImplementedError


class SimpleConnector(Connector):
    """
    Simple connection between roads that don't change width.
    """

    def __init__(
        self,
        road_1: Road,
        index_1: int,
        road_2: Road,
        index_2: int,
        flinger: Flinger,
        scale: float,
    ) -> None:
        super().__init__(road_1, index_1, road_2, index_2, flinger, scale)
        node: OSMNode = road_1.nodes[index_1]
        self.point: np.ndarray = flinger.fling(node.coordinates)

    def draw(self, svg: Drawing) -> None:
        """Draw connection fill."""
        circle = svg.circle(
            self.point,
            self.road_1.width + 1,
            fill=self.road_1.matcher.color.hex,
        )
        svg.add(circle)

    def draw_border(self, svg: Drawing) -> None:
        """Draw connection outline."""
        circle = svg.circle(
            self.point,
            self.road_1.width + 2,
            fill=self.road_1.matcher.border_color.hex,
        )
        svg.add(circle)


class ComplexConnector(Connector):
    """
    Connection between roads that change width.
    """

    def __init__(
        self,
        road_1: Road,
        index_1: int,
        road_2: Road,
        index_2: int,
        flinger: Flinger,
        scale: float,
    ) -> None:
        super().__init__(road_1, index_1, road_2, index_2, flinger, scale)

        length: float = abs(road_2.width - road_1.width) * scale
        road_1.line.shorten(index_1, length)
        road_2.line.shorten(index_2, length)

        node: OSMNode = road_1.nodes[index_1]
        point: np.ndarray = flinger.fling(node.coordinates)

        c1: list[np.ndarray] = get_curve_points(
            road_1, scale, point, road_1.line.points[index_1]
        )
        c2: list[np.ndarray] = get_curve_points(
            road_2, scale, point, road_2.line.points[index_2]
        )
        self.curve_1: PathCommands = [c1[0], "C", c1[1], c2[2], c2[3]]
        self.curve_2: PathCommands = [c2[0], "C", c2[1], c1[2], c1[3]]

    def draw(self, svg: Drawing) -> None:
        """Draw connection fill."""
        path = svg.path(
            d=["M"] + self.curve_1 + ["L"] + self.curve_2 + ["Z"],
            fill=self.road_1.matcher.color.hex,
        )
        svg.add(path)

    def draw_border(self, svg: Drawing) -> None:
        """Draw connection outline."""
        path = svg.path(
            d=["M"] + self.curve_1 + ["L"] + self.curve_2 + ["Z"],
            fill="none",
            stroke=self.road_1.matcher.border_color.hex,
            stroke_width=2,
        )
        svg.add(path)


class Roads:
    """
    Whole road structure.
    """

    def __init__(self) -> None:
        self.roads: list[Road] = []
        self.connections: dict[int, list[tuple[Road, int]]] = {}

    def append(self, road: Road) -> None:
        """Add road and update connections."""
        self.roads.append(road)
        for index in road.nodes[0].id_, road.nodes[-1].id_:
            if index not in self.connections:
                self.connections[index] = []
        self.connections[road.nodes[0].id_].append((road, 0))
        self.connections[road.nodes[-1].id_].append((road, -1))

    def draw(self, svg: Drawing, flinger: Flinger) -> None:
        """Draw whole road system."""
        if not self.roads:
            return

        scale: float = flinger.get_scale(self.roads[0].nodes[0].coordinates)
        layered_roads: dict[float, list[Road]] = {}
        layered_connectors: dict[float, list[Connector]] = {}

        for road in self.roads:
            if road.layer not in layered_roads:
                layered_roads[road.layer] = []
            layered_roads[road.layer].append(road)

        for id_ in self.connections:
            if len(self.connections[id_]) != 2:
                continue
            connected: list[tuple[Road, int]] = self.connections[id_]
            road_1, index_1 = connected[0]
            road_2, index_2 = connected[1]
            connector: Connector
            if road_1.width == road_2.width:
                connector = SimpleConnector(
                    road_1, index_1, road_2, index_2, flinger, scale
                )
            else:
                connector = ComplexConnector(
                    road_1, index_1, road_2, index_2, flinger, scale
                )

            if connector.layer not in layered_connectors:
                layered_connectors[connector.layer] = []
            layered_connectors[connector.layer].append(connector)

        for layer in sorted(layered_roads.keys()):
            roads: list[Road] = sorted(
                layered_roads[layer], key=lambda x: x.matcher.priority
            )
            connectors: list[Connector]
            if layer in layered_connectors:
                connectors = layered_connectors[layer]
            else:
                connectors = []

            for road in roads:
                road.draw(svg, flinger, road.matcher.border_color, 2)
            for connector in connectors:
                connector.draw_border(svg)

            for road in roads:
                road.draw(svg, flinger, road.matcher.color)
            for connector in connectors:
                connector.draw(svg)

            for road in roads:
                road.draw_lanes(svg, flinger, road.matcher.border_color)
