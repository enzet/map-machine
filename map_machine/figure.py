"""
Figures displayed on the map.
"""
from typing import Optional

import numpy as np
from colour import Color
from svgwrite import Drawing

from map_machine.geometry.flinger import Flinger
from map_machine.osm.osm_reader import OSMNode, Tagged
from map_machine.scheme import LineStyle, Scheme

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

from map_machine.geometry.vector import Polyline


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
        self, flinger: Flinger, offset: np.ndarray = np.array((0.0, 0.0))
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


def is_clockwise(polygon: list[OSMNode]) -> bool:
    """
    Return true if polygon nodes are in clockwise order.

    :param polygon: list of OpenStreetMap nodes
    """
    count: float = 0.0
    for index, node in enumerate(polygon):
        next_index: int = 0 if index == len(polygon) - 1 else index + 1
        count += (polygon[next_index].coordinates[0] - node.coordinates[0]) * (
            polygon[next_index].coordinates[1] + node.coordinates[1]
        )
    return count >= 0.0


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
