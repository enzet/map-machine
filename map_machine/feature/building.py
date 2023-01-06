"""Buildings on the map."""
import numpy as np
import svgwrite
from colour import Color
from svgwrite import Drawing
from svgwrite.container import Group
from svgwrite.path import Path

from map_machine.drawing import PathCommands
from map_machine.figure import Figure
from map_machine.geometry.flinger import Flinger
from map_machine.geometry.vector import Segment
from map_machine.osm.osm_reader import OSMNode
from map_machine.scheme import Scheme

BUILDING_MINIMAL_HEIGHT: float = 8.0
BUILDING_SCALE: float = 0.33
LEVEL_HEIGHT: float = 2.5
SHADE_SCALE: float = 0.4


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

        self.is_construction: bool = (
            tags.get("building") == "construction"
            or tags.get("construction") == "yes"
        )
        self.has_walls: bool = tags.get("building") != "roof"

        if self.is_construction:
            self.fill: Color = scheme.get_color("building_construction_color")
            self.stroke: Color = scheme.get_color(
                "building_construction_border_color"
            )
        else:
            if color := tags.get("roof:colour"):
                self.fill = scheme.get_color(color)
                self.stroke: Color = Color(self.fill)
                self.stroke.set_luminance(self.fill.get_luminance() * 0.85)
            else:
                self.fill: Color = scheme.get_color("building_color")
                self.stroke: Color = scheme.get_color("building_border_color")

        self.parts: list[Segment] = []

        for nodes in self.inners + self.outers:
            for i in range(len(nodes) - 1):
                flung_1: np.ndarray = flinger.fling(nodes[i].coordinates)
                flung_2: np.ndarray = flinger.fling(nodes[i + 1].coordinates)
                self.parts.append(Segment(flung_1, flung_2))

        self.parts = sorted(self.parts)

        self.height: float = BUILDING_MINIMAL_HEIGHT
        self.min_height: float = 0.0

        self.wall_color: Color
        if self.is_construction:
            self.wall_color = scheme.get_color("wall_construction_color")
        else:
            self.wall_color = scheme.get_color("wall_color")

        if material := tags.get("building:material"):
            if material in scheme.material_colors:
                self.wall_color = Color(scheme.material_colors[material])

        if color := tags.get("building:colour"):
            self.wall_color = scheme.get_color(color)

        if color := tags.get("colour"):
            self.wall_color = scheme.get_color(color)

        self.wall_bottom_color_1: Color = Color(self.wall_color)
        self.wall_bottom_color_1.set_luminance(
            self.wall_color.get_luminance() * 0.70
        )
        self.wall_bottom_color_2: Color = Color(self.wall_color)
        self.wall_bottom_color_2.set_luminance(
            self.wall_color.get_luminance() * 0.85
        )

        if levels := self.get_float("building:levels"):
            self.height = BUILDING_MINIMAL_HEIGHT + levels * LEVEL_HEIGHT

        if levels := self.get_float("building:min_level"):
            self.min_height = BUILDING_MINIMAL_HEIGHT + levels * LEVEL_HEIGHT

        if height := self.get_length("height"):
            self.height = BUILDING_MINIMAL_HEIGHT + height

        if height := self.get_length("min_height"):
            self.min_height = BUILDING_MINIMAL_HEIGHT + height

    def draw(self, svg: Drawing, flinger: Flinger) -> None:
        """Draw simple building shape."""

        tmp_d = self.get_path(flinger)
        if tmp_d == None:
            return

        path: Path = Path(
            d=tmp_d,
            stroke=self.stroke.hex,
            fill=self.fill.hex,
            stroke_linejoin="round",
        )
        svg.add(path)

    def draw_shade(self, building_shade: Group, flinger: Flinger) -> None:
        """Draw shade casted by the building."""
        scale: float = flinger.get_scale() * SHADE_SCALE
        shift_1: np.ndarray = np.array((scale * self.min_height, 0.0))
        shift_2: np.ndarray = np.array((scale * self.height, 0.0))

        tmp_commands = self.get_path(flinger, shift_1)
        if tmp_commands == None:
            return

        commands: str = tmp_commands
        path: Path = Path(
            commands, fill="#000000", stroke="#000000", stroke_width=1.0
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
        if not self.has_walls:
            return

        shift_1: np.ndarray = np.array(
            (0.0, -previous_height * scale * BUILDING_SCALE)
        )
        shift_2: np.ndarray = np.array((0.0, -height * scale * BUILDING_SCALE))

        for segment in self.parts:
            draw_walls(svg, self, segment, height, shift_1, shift_2)

    def draw_roof(self, svg: Drawing, flinger: Flinger, scale: float) -> None:
        """Draw building roof."""
        tmp_d = self.get_path(
                flinger, np.array([0.0, -self.height * scale * BUILDING_SCALE])
            )
        if tmp_d == None:
            return            

        path: Path = Path(
            d=tmp_d,
            stroke=self.stroke,
            fill="none" if self.is_construction else self.fill.hex,
            stroke_linejoin="round",
        )
        svg.add(path)


def draw_walls(
    svg: svgwrite.Drawing,
    building: Building,
    segment: Segment,
    height: float,
    shift_1: np.ndarray,
    shift_2: np.ndarray,
):
    """
    Draw walls for buildings as a quadrangle.

    Color of the wall is based on illumination.
    """
    color: Color
    if building.is_construction:
        color_part: float = segment.angle * 0.2
        color = Color(
            rgb=(
                building.wall_color.get_red() + color_part,
                building.wall_color.get_green() + color_part,
                building.wall_color.get_blue() + color_part,
            )
        )
    elif height <= 0.25 / BUILDING_SCALE:
        color = building.wall_bottom_color_1
    elif height <= 0.5 / BUILDING_SCALE:
        color = building.wall_bottom_color_2
    else:
        color_part: float = segment.angle * 0.2 - 0.1
        color = Color(
            rgb=(
                max(min(building.wall_color.get_red() + color_part, 1), 0),
                max(min(building.wall_color.get_green() + color_part, 1), 0),
                max(min(building.wall_color.get_blue() + color_part, 1), 0),
            )
        )

    command: PathCommands = [
        "M",
        segment.point_1 + shift_1,
        "L",
        segment.point_2 + shift_1,
        segment.point_2 + shift_2,
        segment.point_1 + shift_2,
        segment.point_1 + shift_1,
        "Z",
    ]
    path: Path = Path(
        d=command,
        fill=color.hex,
        stroke=color.hex,
        stroke_width=1,
        stroke_linejoin="round",
    )
    svg.add(path)
