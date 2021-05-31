"""
Road shape drawing.
"""
from dataclasses import dataclass
from typing import List

import numpy as np
import svgwrite
from shapely.geometry import LineString, Point

from roentgen.flinger import Flinger, angle, turn_by_angle, norm
from roentgen.osm_reader import OSMNode


@dataclass
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
        lanes: List[float],
    ):
        self.point_1: np.array = point_1
        self.point_2: np.array = point_2
        self.left_offset: float = left_offset
        self.right_offset: float = right_offset
        self.lanes: List[float] = lanes

        self.turned = norm(
            turn_by_angle(self.point_2 - self.point_1, np.pi / 2)
        )
        self.right = self.turned * self.right_offset
        self.left = -self.turned * self.left_offset

        self.rm = None
        self.lm = None
        self.rp = None
        self.lp = None

    @classmethod
    def from_nodes(
        cls,
        node_1: OSMNode,
        node_2: OSMNode,
        flinger: Flinger,
        left_offset: float,
        right_offset: float,
        lanes: List[float],
    ) -> "RoadPart":
        """
        Construct road part from OSM nodes.
        """
        return cls(
            flinger.fling(node_1.coordinates),
            flinger.fling(node_2.coordinates),
            left_offset,
            right_offset,
            lanes,
        )

    def update(self):
        """
        Compute additional points.
        """
        if self.rp is not None and self.lp is not None:
            self.rm = self.lp + self.right - self.left
            self.lm = self.rp - self.right + self.left

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
            ("M", self.point_1 + self.right, "L", self.point_2 + self.right),
            fill="none",
            stroke="#FF0000",
            stroke_width=0.5,
        )
        drawing.add(line)
        line = drawing.path(
            ("M", self.point_1 + self.left, "L", self.point_2 + self.left),
            fill="none",
            stroke="#0000FF",
            stroke_width=0.5,
        )
        drawing.add(line)

        if self.rp is not None:
            circle = drawing.circle(self.rp, 2)
            drawing.add(circle)
        if self.lp is not None:
            circle = drawing.circle(self.lp, 2)
            drawing.add(circle)
        if self.rm is not None:
            circle = drawing.circle(self.rm, 2, fill="#FF0000")
            drawing.add(circle)
        if self.lm is not None:
            circle = drawing.circle(self.lm, 2, fill="#0000FF")
            drawing.add(circle)

    def draw(self, drawing: svgwrite.Drawing):
        """
        Draw road part.
        """
        d = [
            "M", self.point_2 + self.right,
            "L", self.point_2 + self.left,
            "L", self.lp,
            "L", self.rp,
            "Z",
        ]
        drawing.add(drawing.path(d, fill="#CCCCCC"))

        d = ["M", self.rm, "L", self.rp, "L", self.lm, "L", self.lp, "Z"]
        drawing.add(drawing.path(d, fill="#C0C0C0"))

    def draw_lanes(self, drawing: svgwrite.Drawing):
        """
        Draw lane delimiters.
        """
        for lane in self.lanes:
            a = self.right - self.turned * lane
            drawing.add(
                drawing.path(
                    ["M", self.point_2 + a, "L", self.point_1 + a],
                    fill="none",
                    stroke="#FFFFFF",
                    stroke_width=2,
                    stroke_dasharray="7,7",
                )
            )


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
            line_1 = LineString(
                [part_1.point_1 + part_1.right, part_1.point_2 + part_1.right]
            )
            line_2 = LineString(
                [part_2.point_1 + part_2.left, part_2.point_2 + part_2.left]
            )
            print(line_1)
            print(line_2)
            a = line_1.intersection(line_2)
            print(a)
            if isinstance(a, Point):
                part_1.rp = np.array((a.x, a.y))
                part_2.lp = np.array((a.x, a.y))
                part_1.update()
                part_2.update()

    def draw(self, drawing: svgwrite.Drawing):
        """
        Draw all road parts and intersection.
        """
        for part in self.parts:
            part.draw(drawing)
        for part in self.parts:
            part.draw_lanes(drawing)

        d = ["M"]
        for part in self.parts:
            d += [part.lp, "L"]
        d[-1] = "Z"

        drawing.add(drawing.path(d, fill="#BBBBBB"))
