"""
Buildings on the map.
"""
from typing import Any, Optional

import numpy as np
from colour import Color
from svgwrite import Drawing
from svgwrite.container import Group
from svgwrite.path import Path

from map_machine.drawing import PathCommands
from map_machine.feature.direction import Segment
from map_machine.figure import Figure
from map_machine.geometry.flinger import Flinger
from map_machine.osm.osm_reader import OSMNode
from map_machine.scheme import Scheme, LineStyle

BUILDING_HEIGHT_SCALE: float = 2.5
BUILDING_MINIMAL_HEIGHT: float = 8.0


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
        shift_1: np.ndarray = np.array((scale * self.min_height, 0.0))
        shift_2: np.ndarray = np.array((scale * self.height, 0.0))
        commands: str = self.get_path(flinger, shift_1)
        path: Path = Path(
            d=commands, fill="#000000", stroke="#000000", stroke_width=1.0
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
                    command, fill="#000000", stroke="#000000", stroke_width=1.0
                )
                building_shade.add(path)

    def draw_walls(
        self, svg: Drawing, height: float, previous_height: float, scale: float
    ) -> None:
        """Draw building walls."""
        shift_1: np.ndarray = np.array((0.0, -previous_height * scale))
        shift_2: np.ndarray = np.array((0.0, -height * scale))
        for segment in self.parts:
            fill: Color
            if height == 2.0:
                fill = Color("#AAAAAA")
            elif height == 4.0:
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
            d=self.get_path(flinger, np.array([0.0, -self.height * scale]))
        )
        path.update(self.line_style.style)
        path.update({"stroke-linejoin": "round"})
        svg.add(path)
