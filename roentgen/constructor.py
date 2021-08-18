"""
Construct Röntgen nodes and ways.
"""
import logging
from datetime import datetime
from hashlib import sha256
from typing import Any, Iterator, Optional, Union

import numpy as np
from colour import Color

from roentgen import ui
from roentgen.color import get_gradient_color
from roentgen.figure import Building, Road, StyledFigure, Tree, DirectionSector
from roentgen.flinger import Flinger

# fmt: off
from roentgen.icon import (
    DEFAULT_SMALL_SHAPE_ID, Icon, IconSet, ShapeExtractor, ShapeSpecification
)
from roentgen.osm_reader import OSMData, OSMNode, OSMRelation, OSMWay
from roentgen.point import Point
from roentgen.scheme import DEFAULT_COLOR, LineStyle, Scheme
from roentgen.ui import TIME_MODE, AUTHOR_MODE
from roentgen.util import MinMax

# fmt: on

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

DEBUG: bool = False
TIME_COLOR_SCALE: list[Color] = [
    Color("#581845"),
    Color("#900C3F"),
    Color("#C70039"),
    Color("#FF5733"),
    Color("#FFC300"),
    Color("#DAF7A6"),
]


def line_center(nodes: list[OSMNode], flinger: Flinger) -> np.array:
    """
    Get geometric center of nodes set.

    :param nodes: node list
    :param flinger: flinger that remap geo positions
    """
    boundary: list[MinMax] = [MinMax(), MinMax()]

    for node in nodes:
        boundary[0].update(node.coordinates[0])
        boundary[1].update(node.coordinates[1])
    center_coordinates = np.array((boundary[0].center(), boundary[1].center()))

    return flinger.fling(center_coordinates), center_coordinates


def get_user_color(text: str, seed: str) -> Color:
    """
    Generate random color based on text.
    """
    if text == "":
        return Color("black")
    return Color("#" + sha256((seed + text).encode("utf-8")).hexdigest()[-6:])


def get_time_color(time: Optional[datetime], boundaries: MinMax) -> Color:
    """
    Generate color based on time.

    :param time: current element creation time
    :param boundaries: minimum and maximum element creation time on the map
    """
    return get_gradient_color(time, boundaries, TIME_COLOR_SCALE)


def glue(ways: list[OSMWay]) -> list[list[OSMNode]]:
    """
    Try to glue ways that share nodes.

    :param ways: ways to glue
    """
    result: list[list[OSMNode]] = []
    to_process: set[OSMWay] = set()

    for way in ways:
        if way.is_cycle():
            result.append(way.nodes)
        else:
            to_process.add(way)

    while to_process:
        way: OSMWay = to_process.pop()
        glued: Optional[OSMWay] = None
        other_way: Optional[OSMWay] = None

        for other_way in to_process:
            glued = way.try_to_glue(other_way)
            if glued:
                break

        if glued:
            to_process.remove(other_way)
            if glued.is_cycle():
                result.append(glued.nodes)
            else:
                to_process.add(glued)
        else:
            result.append(way.nodes)

    return result


def is_cycle(nodes) -> bool:
    """Is way a cycle way or an area boundary."""
    return nodes[0] == nodes[-1]


class Constructor:
    """
    Röntgen node and way constructor.
    """

    def __init__(
        self,
        osm_data: OSMData,
        flinger: Flinger,
        scheme: Scheme,
        icon_extractor: ShapeExtractor,
        check_level=lambda x: True,
        mode: str = "normal",
        seed: str = "",
    ) -> None:
        self.check_level = check_level
        self.mode: str = mode
        self.seed: str = seed
        self.osm_data: OSMData = osm_data
        self.flinger: Flinger = flinger
        self.scheme: Scheme = scheme
        self.icon_extractor = icon_extractor

        self.points: list[Point] = []
        self.figures: list[StyledFigure] = []
        self.buildings: list[Building] = []
        self.roads: list[Road] = []
        self.trees: list[Tree] = []
        self.direction_sectors: list[DirectionSector] = []

        self.heights: set[float] = {2, 4}

    def add_building(self, building: Building) -> None:
        """Add building and update levels."""
        self.buildings.append(building)
        self.heights.add(building.height)
        self.heights.add(building.min_height)

    def construct(self) -> None:
        """Construct nodes, ways, and relations."""
        self.construct_ways()
        self.construct_relations()
        self.construct_nodes()

    def construct_ways(self) -> None:
        """Construct Röntgen ways."""
        for index, way_id in enumerate(self.osm_data.ways):
            ui.progress_bar(
                index,
                len(self.osm_data.ways),
                step=10,
                text="Constructing ways",
            )
            way: OSMWay = self.osm_data.ways[way_id]
            self.construct_line(way, [], [way.nodes])

        ui.progress_bar(-1, len(self.osm_data.ways), text="Constructing ways")

    def construct_line(
        self,
        line: Union[OSMWay, OSMRelation],
        inners: list[list[OSMNode]],
        outers: list[list[OSMNode]],
    ) -> None:
        """
        Way or relation construction.

        :param line: OpenStreetMap way or relation
        :param inners: list of polygons that compose inner boundary
        :param outers: list of polygons that compose outer boundary
        """
        assert len(outers) >= 1

        if not self.check_level(line.tags):
            return

        center_point, center_coordinates = line_center(outers[0], self.flinger)
        if self.mode in [AUTHOR_MODE, TIME_MODE]:
            color: Color
            if self.mode == AUTHOR_MODE:
                color = get_user_color(line.user, self.seed)
            else:  # self.mode == TIME_MODE
                color = get_time_color(line.timestamp, self.osm_data.time)
            self.draw_special_mode(inners, line, outers, color)
            return

        if not line.tags:
            return

        if "building:part" in line.tags or "building" in line.tags:
            self.add_building(
                Building(line.tags, inners, outers, self.flinger, self.scheme)
            )

        road_matcher = self.scheme.get_road(line.tags)
        if road_matcher:
            self.roads.append(Road(line.tags, inners, outers, road_matcher))
            return

        line_styles: list[LineStyle] = self.scheme.get_style(line.tags)

        for line_style in line_styles:
            self.figures.append(
                StyledFigure(line.tags, inners, outers, line_style)
            )
            if (
                line.get_tag("area") == "yes"
                or is_cycle(outers[0])
                and line.get_tag("area") != "no"
                and self.scheme.is_area(line.tags)
            ):
                processed: set[str] = set()

                priority: int
                icon_set: IconSet
                icon_set, priority = self.scheme.get_icon(
                    self.icon_extractor, line.tags, processed
                )
                labels = self.scheme.construct_text(line.tags, "all", processed)
                point: Point = Point(
                    icon_set,
                    labels,
                    line.tags,
                    processed,
                    center_point,
                    center_coordinates,
                    is_for_node=False,
                    priority=priority,
                )  # fmt: skip
                self.points.append(point)

        if not line_styles:
            if DEBUG:
                style: dict[str, Any] = {
                    "fill": "none",
                    "stroke": Color("red").hex,
                    "stroke-width": 1,
                }
                figure: StyledFigure = StyledFigure(
                    line.tags, inners, outers, LineStyle(style, 1000)
                )
                self.figures.append(figure)

            processed: set[str] = set()

            priority: int
            icon_set: IconSet
            icon_set, priority = self.scheme.get_icon(
                self.icon_extractor, line.tags, processed
            )
            labels = self.scheme.construct_text(line.tags, "all", processed)
            point: Point = Point(
                icon_set, labels, line.tags, processed, center_point,
                center_coordinates, is_for_node=False, priority=priority,
            )  # fmt: skip
            self.points.append(point)

    def draw_special_mode(self, inners, line, outers, color) -> None:
        """
        Add figure for special mode: time or author.
        """
        style: dict[str, Any] = {
            "fill": "none",
            "stroke": color.hex,
            "stroke-width": 1,
        }
        self.figures.append(
            StyledFigure(line.tags, inners, outers, LineStyle(style))
        )

    def construct_relations(self) -> None:
        """
        Construct Röntgen ways from OSM relations.
        """
        for relation_id in self.osm_data.relations:
            relation: OSMRelation = self.osm_data.relations[relation_id]
            tags = relation.tags
            if not self.check_level(tags):
                continue
            if "type" not in tags or tags["type"] != "multipolygon":
                continue
            inner_ways: list[OSMWay] = []
            outer_ways: list[OSMWay] = []
            for member in relation.members:
                if member.type_ == "way":
                    if member.role == "inner":
                        if member.ref in self.osm_data.ways:
                            inner_ways.append(self.osm_data.ways[member.ref])
                    elif member.role == "outer":
                        if member.ref in self.osm_data.ways:
                            outer_ways.append(self.osm_data.ways[member.ref])
                    else:
                        logging.warning(f'Unknown member role "{member.role}".')
            if outer_ways:
                inners_path: list[list[OSMNode]] = glue(inner_ways)
                outers_path: list[list[OSMNode]] = glue(outer_ways)
                self.construct_line(relation, inners_path, outers_path)

    def construct_nodes(self) -> None:
        """Draw nodes."""
        sorted_node_ids: Iterator[int] = sorted(
            self.osm_data.nodes.keys(),
            key=lambda x: -self.osm_data.nodes[x].coordinates[0],
        )

        for index, node_id in enumerate(sorted_node_ids):
            ui.progress_bar(
                index, len(self.osm_data.nodes), text="Constructing nodes"
            )
            self.construct_node(self.osm_data.nodes[node_id])
        ui.progress_bar(-1, len(self.osm_data.nodes), text="Constructing nodes")

    def construct_node(self, node: OSMNode) -> None:
        """Draw one node."""
        tags = node.tags
        if not self.check_level(tags):
            return

        processed: set[str] = set()

        flung = self.flinger.fling(node.coordinates)

        priority: int
        icon_set: IconSet
        draw_outline: bool = True

        if self.mode in [TIME_MODE, AUTHOR_MODE]:
            if not tags:
                return
            color: Color = DEFAULT_COLOR
            if self.mode == AUTHOR_MODE:
                color = get_user_color(node.user, self.seed)
            if self.mode == TIME_MODE:
                color = get_time_color(node.timestamp, self.osm_data.time)
            dot = self.icon_extractor.get_shape(DEFAULT_SMALL_SHAPE_ID)
            icon_set = IconSet(
                Icon([ShapeSpecification(dot, color)]), [], set()
            )
            point: Point = Point(
                icon_set, [], tags, processed, flung, node.coordinates,
                draw_outline=False
            )  # fmt: skip
            self.points.append(point)
            return

        icon_set, priority = self.scheme.get_icon(
            self.icon_extractor, tags, processed
        )
        labels = self.scheme.construct_text(tags, "all", processed)
        self.scheme.process_ignored(tags, processed)

        if node.get_tag("natural") == "tree" and (
            "diameter_crown" in node.tags or "circumference" in node.tags
        ):
            self.trees.append(Tree(tags, node.coordinates, flung))
            return

        if "direction" in node.tags or "camera:direction" in node.tags:
            self.direction_sectors.append(DirectionSector(tags, flung))
        point: Point = Point(
            icon_set, labels, tags, processed, flung, node.coordinates,
            priority=priority, draw_outline=draw_outline
        )  # fmt: skip
        self.points.append(point)
