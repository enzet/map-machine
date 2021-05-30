"""
Simple OpenStreetMap renderer.
"""
from typing import Any, Dict

import numpy as np
import svgwrite
from colour import Color
from svgwrite.container import Group
from svgwrite.path import Path
from svgwrite.shapes import Rect

from roentgen import ui
from roentgen.constructor import Building, Constructor, Road, Segment
from roentgen.direction import DirectionSet, Sector
from roentgen.flinger import Flinger
from roentgen.icon import ShapeExtractor
from roentgen.osm_reader import Map
from roentgen.point import Occupied, Point
from roentgen.scheme import Scheme

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

ICONS_FILE_NAME: str = "icons/icons.svg"
TAGS_FILE_NAME: str = "scheme/default.yml"
MISSING_TAGS_FILE_NAME: str = "missing_tags.yml"

AUTHOR_MODE = "user-coloring"
CREATION_TIME_MODE = "time"


class Painter:
    """
    Map drawing.
    """

    def __init__(
        self,
        map_: Map,
        flinger: Flinger,
        svg: svgwrite.Drawing,
        icon_extractor: ShapeExtractor,
        scheme: Scheme,
        show_missing_tags: bool = False,
        overlap: int = 12,
        mode: str = "normal",
        label_mode: str = "main"
    ):
        self.show_missing_tags: bool = show_missing_tags
        self.overlap: int = overlap
        self.mode: str = mode
        self.label_mode: str = label_mode

        self.map_: Map = map_
        self.flinger: Flinger = flinger
        self.svg: svgwrite.Drawing = svg
        self.icon_extractor = icon_extractor
        self.scheme: Scheme = scheme

        self.background_color: Color = self.scheme.get_color("background_color")
        if self.mode in [AUTHOR_MODE, CREATION_TIME_MODE]:
            self.background_color: Color = Color("#111111")

    def draw(self, constructor: Constructor) -> None:
        """
        Draw map.
        """
        self.svg.add(
            Rect((0, 0), self.flinger.size, fill=self.background_color)
        )
        ways = sorted(constructor.figures, key=lambda x: x.line_style.priority)
        ways_length: int = len(ways)
        for index, way in enumerate(ways):
            ui.progress_bar(index, ways_length, step=10, text="Drawing ways")
            path_commands: str = way.get_path(self.flinger)
            if path_commands:
                path = Path(d=path_commands)
                path.update(way.line_style.style)
                self.svg.add(path)
        ui.progress_bar(-1, 0, text="Drawing ways")

        roads = sorted(
            constructor.roads, key=lambda x: x.matcher.priority
        )
        for road in roads:
            self.draw_road(road, road.matcher.border_color, 2)
        for road in roads:
            self.draw_road(road, road.matcher.color)

        # Trees

        for node in constructor.points:
            if not (node.get_tag("natural") == "tree" and
                    ("diameter_crown" in node.tags or
                     "circumference" in node.tags)):
                continue
            if "circumference" in node.tags:
                if "diameter_crown" in node.tags:
                    opacity = 0.7
                    radius = float(node.tags["diameter_crown"]) / 2
                else:
                    opacity = 0.3
                    radius = 2
                self.svg.add(self.svg.circle(
                    node.point,
                    radius * self.flinger.get_scale(node.coordinates),
                    fill=self.scheme.get_color("evergreen_color"),
                    opacity=opacity))
                self.svg.add(self.svg.circle(
                    node.point,
                    float(node.tags["circumference"]) / 2 / np.pi *
                    self.flinger.get_scale(node.coordinates),
                    fill="#B89A74"))

        # Draw building shade.

        building_shade: Group = Group(opacity=0.1)
        length: float = self.flinger.get_scale()

        for building in constructor.buildings:
            shift = np.array((length * building.get_levels(), 0))
            for nodes in building.inners + building.outers:
                for i in range(len(nodes) - 1):  # type: int
                    flung_1 = self.flinger.fling(nodes[i].coordinates)
                    flung_2 = self.flinger.fling(nodes[i + 1].coordinates)
                    building_shade.add(Path(
                        ("M", flung_1, "L", flung_2, np.add(flung_2, shift),
                         np.add(flung_1, shift), "Z"),
                        fill="#000000", stroke="#000000", stroke_width=1))

        self.svg.add(building_shade)

        # Draw buildings.

        previous_level: float = 0
        level_height: float = self.flinger.get_scale()
        level_count: int = len(constructor.levels)

        for index, level in enumerate(sorted(constructor.levels)):
            ui.progress_bar(
                index, level_count, step=1, text="Drawing buildings")
            fill: Color()
            for way in constructor.buildings:  # type: Building
                if way.get_levels() < level:
                    continue
                shift_1 = [0, -previous_level * level_height]
                shift_2 = [0, -level * level_height]
                for segment in way.parts:  # type: Segment
                    if level == 0.5:
                        fill = Color("#AAAAAA")
                    elif level == 1:
                        fill = Color("#C3C3C3")
                    else:
                        color_part: float = 0.8 + segment.angle * 0.2
                        fill = Color(rgb=(color_part, color_part, color_part))

                    self.svg.add(self.svg.path(
                        d=("M", segment.point_1 + shift_1, "L",
                           segment.point_2 + shift_1,
                           segment.point_2 + shift_2,
                           segment.point_1 + shift_2,
                           segment.point_1 + shift_1, "Z"),
                        fill=fill.hex, stroke=fill.hex, stroke_width=1,
                        stroke_linejoin="round"))

            # Draw building roofs.

            for way in constructor.buildings:  # type: Building
                if way.get_levels() == level:
                    shift = np.array([0, -way.get_levels() * level_height])
                    path_commands: str = way.get_path(self.flinger, shift)
                    path = Path(d=path_commands, opacity=1)
                    path.update(way.line_style.style)
                    path.update({"stroke-linejoin": "round"})
                    self.svg.add(path)

            previous_level = level

        ui.progress_bar(-1, level_count, step=1, text="Drawing buildings")

        # Directions

        for node in constructor.points:  # type: Point

            angle = None
            is_revert_gradient: bool = False

            if node.get_tag("man_made") == "surveillance":
                direction = node.get_tag("camera:direction")
                if "camera:angle" in node.tags:
                    angle = float(node.get_tag("camera:angle"))
                if "angle" in node.tags:
                    angle = float(node.get_tag("angle"))
                direction_radius: float = 25
                direction_color: Color = (
                    self.scheme.get_color("direction_camera_color")
                )
            elif node.get_tag("traffic_sign") == "stop":
                direction = node.get_tag("direction")
                direction_radius: float = 25
                direction_color: Color = Color("red")
            else:
                direction = node.get_tag("direction")
                direction_radius: float = 50
                direction_color: Color = (
                    self.scheme.get_color("direction_view_color")
                )
                is_revert_gradient = True

            if not direction:
                continue

            point = (node.point.astype(int)).astype(float)

            if angle:
                paths = [Sector(direction, angle).draw(point, direction_radius)]
            else:
                paths = DirectionSet(direction).draw(point, direction_radius)

            for path in paths:
                gradient = self.svg.defs.add(self.svg.radialGradient(
                    center=point, r=direction_radius,
                    gradientUnits="userSpaceOnUse"))
                if is_revert_gradient:
                    (
                        gradient
                            .add_stop_color(0, direction_color.hex, opacity=0)
                            .add_stop_color(1, direction_color.hex, opacity=0.7)
                    )
                else:
                    (
                        gradient
                            .add_stop_color(0, direction_color.hex, opacity=0.4)
                            .add_stop_color(1, direction_color.hex, opacity=0)
                    )
                self.svg.add(self.svg.path(
                    d=["M", point] + path + ["L", point, "Z"],
                    fill=gradient.get_paint_server()))

        # All other points

        if self.overlap == 0:
            occupied = None
        else:
            occupied = Occupied(
                self.flinger.size[0], self.flinger.size[1], self.overlap)

        nodes = sorted(constructor.points, key=lambda x: -x.priority)
        steps: int = len(nodes)

        for index, node in enumerate(nodes):  # type: int, Point
            if (node.get_tag("natural") == "tree" and
                    ("diameter_crown" in node.tags or
                     "circumference" in node.tags)):
                continue
            ui.progress_bar(
                index, steps * 3, step=10, text="Drawing main icons"
            )
            node.draw_main_shapes(self.svg, occupied)

        for index, point in enumerate(nodes):  # type: int, Point
            ui.progress_bar(
                steps + index, steps * 3, step=10, text="Drawing extra icons"
            )
            point.draw_extra_shapes(self.svg, occupied)

        for index, point in enumerate(nodes):  # type: int, Point
            ui.progress_bar(
                steps * 2 + index, steps * 3, step=10, text="Drawing texts"
            )
            if (
                self.mode not in [CREATION_TIME_MODE, AUTHOR_MODE]
                and self.label_mode != "no"
            ):
                point.draw_texts(self.svg, occupied, self.label_mode)

        ui.progress_bar(-1, len(nodes), step=10, text="Drawing nodes")

    def draw_road(
        self, road: Road, color: Color, extra_width: float = 0
    ) -> None:
        self.flinger.get_scale()
        if road.width is not None:
            width = road.width
        else:
            width = road.matcher.default_width
        scale = self.flinger.get_scale(road.outers[0][0].coordinates)
        path_commands: str = road.get_path(self.flinger)
        path = Path(d=path_commands)
        path.update({
            "fill": "none",
            "stroke": color.hex,
            "stroke-linecap": "round",
            "stroke-linejoin": "round",
            "stroke-width": scale * width + extra_width
        })
        self.svg.add(path)


def check_level_number(tags: Dict[str, Any], level: float):
    """
    Check if element described by tags is no the specified level.
    """
    if "level" in tags:
        levels = map(float, tags["level"].replace(",", ".").split(";"))
        if level not in levels:
            return False
    else:
        return False
    return True


def check_level_overground(tags: Dict[str, Any]) -> bool:
    """
    Check if element described by tags is overground.
    """
    if "level" in tags:
        try:
            levels = map(float, tags["level"].replace(",", ".").split(";"))
            for level in levels:
                if level <= 0:
                    return False
        except ValueError:
            pass
    if "layer" in tags:
        try:
            levels = map(float, tags["layer"].replace(",", ".").split(";"))
            for level in levels:
                if level <= 0:
                    return False
        except ValueError:
            pass
    if "parking" in tags and tags["parking"] == "underground":
        return False
    return True
