"""
Road shape drawing.
"""
from dataclasses import dataclass
from typing import List

import numpy as np
import svgwrite

from roentgen.constructor import Road
from roentgen.flinger import Flinger
from roentgen.vector import angle, turn_by_angle, norm, Line
from roentgen.osm_reader import OSMNode


@dataclass
class Lane:
    """
    Road lane specification.
    """

    width: float  # Width in meters


class RoadPart:
    """
    Line part of the road.
    """

    def __init__(
        self,
        point_1: np.array,
        point_2: np.array,
        left_offset: float,
        right_offset: float,
        lanes: List[Lane],
    ):
        """
        :param point_1: start point of the road part
        :param point_2: end point of the road part
        :param left_offset: offset from the central line to the left border
        :param right_offset:  offset from the central line to the right border
        :param lanes: lane specification
        """
        self.point_1: np.array = point_1
        self.point_2: np.array = point_2
        self.left_offset: float = left_offset
        self.right_offset: float = right_offset
        self.lanes: List[Lane] = lanes

        self.turned: np.array = norm(
            turn_by_angle(self.point_2 - self.point_1, np.pi / 2)
        )
        self.right_vector: np.array = self.turned * self.right_offset
        self.left_vector: np.array = -self.turned * self.left_offset

        self.right_connection: np.array = None
        self.left_connection: np.array = None
        self.right_projection: np.array = None
        self.left_projection: np.array = None

    @classmethod
    def from_nodes(
        cls,
        node_1: OSMNode,
        node_2: OSMNode,
        flinger: Flinger,
        road: Road,
    ) -> "RoadPart":
        """
        Construct road part from OSM nodes.
        """
        left_offset: float = road.width / 2
        right_offset: float = road.width / 2
        lanes = [Lane(road.width / road.lanes)] * road.lanes

        return cls(
            flinger.fling(node_1.coordinates),
            flinger.fling(node_2.coordinates),
            left_offset,
            right_offset,
            lanes,
        )

    def update(self) -> None:
        """
        Compute additional points.
        """
        if (
            self.right_connection is not None
            and self.left_connection is not None
        ):
            self.right_projection = (
                self.left_connection + self.right_vector - self.left_vector
            )
            self.left_projection = (
                self.right_connection - self.right_vector + self.left_vector
            )

    def get_angle(self) -> float:
        """
        Get an angle between line and x axis.
        """
        return angle(self.point_2 - self.point_1)

    def draw_debug(self, drawing: svgwrite.Drawing):
        """
        Draw some debug lines.
        """
        line = drawing.path(
            ("M", self.point_1, "L", self.point_2),
            fill="none",
            stroke="#000000",
        )
        drawing.add(line)
        line = drawing.path(
            (
                "M", self.point_1 + self.right_vector,
                "L", self.point_2 + self.right_vector,
            ),
            fill="none",
            stroke="#FF0000",
            stroke_width=0.5,
        )
        drawing.add(line)
        line = drawing.path(
            (
                "M", self.point_1 + self.left_vector,
                "L", self.point_2 + self.left_vector,
            ),
            fill="none",
            stroke="#0000FF",
            stroke_width=0.5,
        )
        drawing.add(line)

        if self.right_connection is not None:
            circle = drawing.circle(self.right_connection, 1.2)
            drawing.add(circle)
        if self.left_connection is not None:
            circle = drawing.circle(self.left_connection, 1.2)
            drawing.add(circle)
        if self.right_projection is not None:
            circle = drawing.circle(self.right_projection, 1.2, fill="#FF0000")
            drawing.add(circle)
        if self.left_projection is not None:
            circle = drawing.circle(self.left_projection, 1.2, fill="#0000FF")
            drawing.add(circle)

        self.draw_entrance(drawing, True)

    def draw(self, drawing: svgwrite.Drawing):
        """
        Draw road part.
        """
        path_commands = [
            "M", self.point_2 + self.right_vector,
            "L", self.point_2 + self.left_vector,
            "L", self.left_connection,
            "L", self.right_connection,
            "Z",
        ]
        drawing.add(drawing.path(path_commands, fill="#CCCCCC"))

        # self.draw_entrance(drawing, False)

    def draw_entrance(self, drawing: svgwrite.Drawing, is_debug: bool):
        path_commands = [
            "M", self.right_projection,
            "L", self.right_connection,
            "L", self.left_projection,
            "L", self.left_connection,
            "Z",
        ]
        if is_debug:
            path = drawing.path(
                path_commands, fill="none", stroke="#880088", stroke_width=0.5
            )
            drawing.add(path)
        else:
            drawing.add(drawing.path(path_commands, fill="#BBBBBB"))

    def draw_lanes(self, drawing: svgwrite.Drawing):
        """
        Draw lane delimiters.
        """
        for lane in self.lanes:
            a = self.right_vector - self.turned * lane.width
            path = drawing.path(
                ["M", self.point_2 + a, "L", self.point_1 + a],
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

    def __init__(self, parts: List[RoadPart]):
        self.parts: List[RoadPart] = sorted(parts, key=lambda x: x.get_angle())

        for index in range(len(self.parts)):
            next_index: int = 0 if index == len(self.parts) - 1 else index + 1
            part_1 = self.parts[index]
            part_2 = self.parts[next_index]
            line_1 = Line(
                part_1.point_1 + part_1.right_vector,
                part_1.point_2 + part_1.right_vector,
            )
            line_2 = Line(
                part_2.point_1 + part_2.left_vector,
                part_2.point_2 + part_2.left_vector,
            )
            a = line_1.get_intersection_point(line_2)
            part_1.right_connection = a
            part_2.left_connection = a
            part_1.update()
            part_2.update()

    def draw(self, drawing: svgwrite.Drawing, is_debug: bool = False):
        """
        Draw all road parts and intersection.
        """
        path_commands = ["M"]
        for part in self.parts:
            path_commands += [part.left_connection, "L"]
        path_commands[-1] = "Z"

        if is_debug:
            drawing.add(drawing.path(path_commands, fill="#DDFFDD"))

        for part in self.parts:
            if is_debug:
                part.draw_debug(drawing)
            else:
                part.draw(drawing)
        if not is_debug:
            for part in self.parts:
                part.draw_lanes(drawing)
            drawing.add(drawing.path(path_commands, fill="#AAAAAA"))
