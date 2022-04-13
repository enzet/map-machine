"""
Figures displayed on the map.
"""
from typing import Any, Dict, Iterator, List, Optional
from svgwrite import Drawing

import numpy as np

from map_machine.geometry.flinger import Flinger
from map_machine.osm.osm_reader import OSMNode, Tagged
from map_machine.scheme import LineStyle

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

from map_machine.geometry.vector import Polyline


class Figure(Tagged):
    """Some figure on the map: way or area."""

    def __init__(
        self,
        tags: Dict[str, str],
        inners: List[List[OSMNode]],
        outers: List[List[OSMNode]],
    ) -> None:
        super().__init__(tags)

        if inners and outers:
            self.inners: List[List[OSMNode]] = list(map(make_clockwise, inners))
            self.outers: List[List[OSMNode]] = list(
                map(make_counter_clockwise, outers)
            )
        else:
            self.inners = inners
            self.outers = outers

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


class StyledFigure(Figure):
    """Figure with stroke and fill style."""

    def __init__(
        self,
        tags: Dict[str, str],
        inners: List[List[OSMNode]],
        outers: List[List[OSMNode]],
        line_style: LineStyle,
    ) -> None:
        super().__init__(tags, inners, outers)
        self.line_style: LineStyle = line_style

    def get_path(
        self,
        flinger: Flinger,
        offset: np.ndarray = np.array((0.0, 0.0)),
    ) -> str:
        """
        Get SVG path commands.

        :param flinger: converter for geo coordinates
        :param offset: offset vector
        """
        path: str = ""

        for outer_nodes in self.outers:
            commands: str = get_path(
                outer_nodes, offset, flinger, self.line_style.parallel_offset
            )
            path += f"{commands} "

        for inner_nodes in self.inners:
            commands: str = get_path(
                inner_nodes, offset, flinger, self.line_style.parallel_offset
            )
            path += f"{commands} "

        return path


def is_clockwise(polygon: List[OSMNode]) -> bool:
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


def get_path(
    nodes: List[OSMNode],
    shift: np.ndarray,
    flinger: Flinger,
    parallel_offset: float = 0.0,
) -> str:
    """Construct SVG path commands from nodes."""
    return Polyline(
        [flinger.fling(node.coordinates) + shift for node in nodes]
    ).get_path(parallel_offset)
