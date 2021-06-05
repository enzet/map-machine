"""
WIP: road shape drawing.
"""
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import svgwrite

from roentgen.flinger import Flinger
from roentgen.vector import angle, turn_by_angle, norm, Line
from roentgen.osm_reader import OSMNode


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
        self.is_forward = is_forward

    def get_width(self, scale: float):
        """
        Get lane width.  We use standard 3.7 m lane.
        """
        if self.width is None:
            return 3.7 * scale
        return self.width * scale


class RoadPart:
    """
    Line part of the road.
    """

    def __init__(
        self,
        point_1: np.array,
        point_2: np.array,
        lanes: List[Lane],
        scale: False,
    ):
        """
        :param point_1: start point of the road part
        :param point_2: end point of the road part
        :param lanes: lane specification
        """
        self.point_1: np.array = point_1
        self.point_2: np.array = point_2
        self.lanes: List[Lane] = lanes
        if lanes:
            self.width = sum(map(lambda x: x.get_width(scale), lanes))
        else:
            self.width = 1
        self.left_offset: float = self.width / 2
        self.right_offset: float = self.width / 2

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
        road,
        scale,
    ) -> "RoadPart":
        """
        Construct road part from OSM nodes.
        """
        lanes = [Lane(road.width / road.lanes)] * road.lanes

        return cls(
            flinger.fling(node_1.coordinates),
            flinger.fling(node_2.coordinates),
            lanes,
            scale,
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
                self.point_a = self.point_1 + max_ * norm(self.point_middle - self.point_1)
                self.right_outer = self.point_a + self.right_vector
                self.left_outer = self.point_a + self.left_vector
            else:
                self.point_a = self.point_middle

    def get_angle(self) -> float:
        """
        Get an angle between line and x axis.
        """
        return angle(self.point_2 - self.point_1)

    def draw_normal(self, drawing: svgwrite.Drawing):
        """
        Draw some debug lines.
        """
        line = drawing.path(
            ("M", self.point_1, "L", self.point_2),
            fill="none",
            stroke="#8888FF",
            stroke_width=self.width,
        )
        drawing.add(line)

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

        opacity: float = 0.4
        radius: float = 2

        if self.right_connection is not None:
            circle = drawing.circle(self.right_connection, radius, fill="#FF0000", opacity=opacity)
            drawing.add(circle)
        if self.left_connection is not None:
            circle = drawing.circle(self.left_connection, radius, fill="#0000FF", opacity=opacity)
            drawing.add(circle)

        if self.right_projection is not None:
            circle = drawing.circle(self.right_projection, radius, fill="#FF0000", opacity=opacity)
            drawing.add(circle)
        if self.left_projection is not None:
            circle = drawing.circle(self.left_projection, radius, fill="#0000FF", opacity=opacity)
            drawing.add(circle)

        if self.right_projection is not None:
            circle = drawing.circle(self.right_outer, radius, fill="#FF0000", opacity=opacity)
            drawing.add(circle)
        if self.left_projection is not None:
            circle = drawing.circle(self.left_outer, radius, fill="#0000FF", opacity=opacity)
            drawing.add(circle)

        circle = drawing.circle(self.point_a, radius, fill="#000000")
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

    def draw_entrance(self, drawing: svgwrite.Drawing, is_debug: bool = False):
        """
        Draw intersection entrance part.
        """
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
            drawing.add(drawing.path(path_commands, fill="#88FF88"))

    def draw_lanes(self, drawing: svgwrite.Drawing, scale: float):
        """
        Draw lane delimiters.
        """
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

    def __init__(self, parts: List[RoadPart]):
        self.parts: List[RoadPart] = sorted(parts, key=lambda x: x.get_angle())

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
            intersection: np.array = line_1.get_intersection_point(line_2)
            part_1.right_connection = intersection
            part_1.update()
            part_2.left_connection = intersection
            part_2.update()

    def draw(
        self, drawing: svgwrite.Drawing, scale: float, is_debug: bool = False
    ) -> None:
        """
        Draw all road parts and intersection.
        """
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
            drawing.add(drawing.path(outer_commands, fill="#0000FF", opacity=0.2))
            drawing.add(drawing.path(inner_commands, fill="#FF0000", opacity=0.2))

        for part in self.parts:
            if is_debug:
                part.draw_debug(drawing)
            else:
                part.draw_entrance(drawing)
        if not is_debug:
            # for part in self.parts:
            #     part.draw_lanes(drawing, scale)
            drawing.add(drawing.path(inner_commands, fill="#FF8888"))
