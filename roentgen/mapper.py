"""
Simple OpenStreetMap renderer.
"""
from typing import Any, Iterator

import numpy as np
import svgwrite
from colour import Color
from svgwrite.container import Group
from svgwrite.path import Path
from svgwrite.shapes import Rect

from roentgen import ui
from roentgen.constructor import Constructor
from roentgen.figure import Road
from roentgen.flinger import Flinger
from roentgen.osm_reader import OSMNode
from roentgen.point import Occupied
from roentgen.road import Intersection, RoadPart
from roentgen.scheme import Scheme
from roentgen.ui import AUTHOR_MODE, TIME_MODE

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


class Map:
    """
    Map drawing.
    """

    def __init__(
        self,
        flinger: Flinger,
        svg: svgwrite.Drawing,
        scheme: Scheme,
        overlap: int = 12,
        mode: str = "normal",
        label_mode: str = "main",
    ):
        self.overlap: int = overlap
        self.mode: str = mode
        self.label_mode: str = label_mode

        self.flinger: Flinger = flinger
        self.svg: svgwrite.Drawing = svg
        self.scheme: Scheme = scheme

        self.background_color: Color = self.scheme.get_color("background_color")
        if self.mode in [AUTHOR_MODE, TIME_MODE]:
            self.background_color: Color = Color("#111111")

    def draw(self, constructor: Constructor) -> None:
        """Draw map."""
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

        roads: Iterator[Road] = sorted(
            constructor.roads, key=lambda x: x.matcher.priority
        )
        for road in roads:
            self.draw_road(road, road.matcher.border_color, 2)
        for road in roads:
            self.draw_road(road, road.matcher.color)

        for tree in constructor.trees:
            tree.draw(self.svg, self.flinger, self.scheme)

        for direction_sector in constructor.direction_sectors:
            direction_sector.draw(self.svg, self.scheme)

        self.draw_buildings(constructor)

        # All other points

        if self.overlap == 0:
            occupied = None
        else:
            occupied = Occupied(
                self.flinger.size[0], self.flinger.size[1], self.overlap
            )

        nodes = sorted(constructor.points, key=lambda x: -x.priority)
        steps: int = len(nodes)

        for index, node in enumerate(nodes):
            ui.progress_bar(
                index, steps * 3, step=10, text="Drawing main icons"
            )
            node.draw_main_shapes(self.svg, occupied)

        for index, point in enumerate(nodes):
            ui.progress_bar(
                steps + index, steps * 3, step=10, text="Drawing extra icons"
            )
            point.draw_extra_shapes(self.svg, occupied)

        for index, point in enumerate(nodes):
            ui.progress_bar(
                steps * 2 + index, steps * 3, step=10, text="Drawing texts"
            )
            if (
                self.mode not in [TIME_MODE, AUTHOR_MODE]
                and self.label_mode != "no"
            ):
                point.draw_texts(self.svg, occupied, self.label_mode)

        ui.progress_bar(-1, len(nodes), step=10, text="Drawing nodes")

    def draw_buildings(self, constructor: Constructor) -> None:
        """Draw buildings: shade, walls, and roof."""
        building_shade: Group = Group(opacity=0.1)
        scale: float = self.flinger.get_scale() / 3.0
        for building in constructor.buildings:
            building.draw_shade(building_shade, self.flinger)
        self.svg.add(building_shade)

        previous_height: float = 0
        count: int = len(constructor.heights)
        for index, height in enumerate(sorted(constructor.heights)):
            ui.progress_bar(index, count, step=1, text="Drawing buildings")
            fill: Color()
            for building in constructor.buildings:
                if building.height < height or building.min_height > height:
                    continue
                building.draw_walls(self.svg, height, previous_height, scale)

            for building in constructor.buildings:
                if building.height == height:
                    building.draw_roof(self.svg, self.flinger, scale)

            previous_height = height

        ui.progress_bar(-1, count, step=1, text="Drawing buildings")

    def draw_road(
        self, road: Road, color: Color, extra_width: float = 0
    ) -> None:
        """
        Draw road as simple SVG path.
        """
        self.flinger.get_scale()
        if road.width is not None:
            width = road.width
        else:
            width = road.matcher.default_width
        scale = self.flinger.get_scale(road.outers[0][0].coordinates)
        path_commands: str = road.get_path(self.flinger)
        path = Path(d=path_commands)
        style: dict[str, Any] = {
            "fill": "none",
            "stroke": color.hex,
            "stroke-linecap": "round",
            "stroke-linejoin": "round",
            "stroke-width": scale * width + extra_width,
        }
        path.update(style)
        self.svg.add(path)

    def draw_roads(self, roads: Iterator[Road]) -> None:
        """
        Draw road as simple SVG path.
        """
        nodes: dict[OSMNode, set[RoadPart]] = {}

        for road in roads:
            for index in range(len(road.outers[0]) - 1):
                node_1: OSMNode = road.outers[0][index]
                node_2: OSMNode = road.outers[0][index + 1]
                point_1: np.array = self.flinger.fling(node_1.coordinates)
                point_2: np.array = self.flinger.fling(node_2.coordinates)
                scale: float = self.flinger.get_scale(node_1.coordinates)
                part_1: RoadPart = RoadPart(point_1, point_2, road.lanes, scale)
                part_2: RoadPart = RoadPart(point_2, point_1, road.lanes, scale)
                # part_1.draw_normal(self.svg)

                for node in node_1, node_2:
                    if node not in nodes:
                        nodes[node] = set()

                nodes[node_1].add(part_1)
                nodes[node_2].add(part_2)

        for node in nodes:
            parts = nodes[node]
            if len(parts) < 4:
                continue
            scale: float = self.flinger.get_scale(node.coordinates)
            intersection: Intersection = Intersection(list(parts))
            intersection.draw(self.svg, scale, True)


def check_level_number(tags: dict[str, Any], level: float):
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


def check_level_overground(tags: dict[str, Any]) -> bool:
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
