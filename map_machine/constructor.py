"""Construct Map Machine nodes and ways."""

import logging
import sys
from datetime import datetime
from hashlib import sha256
from typing import Any, Iterator, Optional, Union

import numpy as np
from colour import Color

from map_machine.color import get_gradient_color
from map_machine.feature.building import Building, BUILDING_SCALE
from map_machine.feature.crater import Crater
from map_machine.feature.direction import DirectionSector
from map_machine.feature.road import Road, Roads
from map_machine.feature.tree import Tree
from map_machine.figure import StyledFigure
from map_machine.geometry.flinger import Flinger
from map_machine.map_configuration import DrawingMode, MapConfiguration
from map_machine.osm.osm_reader import (
    OSMData,
    OSMNode,
    OSMRelation,
    OSMWay,
    parse_levels,
    Tags,
)
from map_machine.pictogram.icon import (
    DEFAULT_SMALL_SHAPE_ID,
    Icon,
    IconSet,
    Shape,
    ShapeExtractor,
    ShapeSpecification,
)
from map_machine.pictogram.point import Point
from map_machine.scheme import LineStyle, RoadMatcher, Scheme
from map_machine.text import Label, TextConstructor
from map_machine.ui.cli import BuildingMode
from map_machine.util import MinMax

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


def line_center(
    nodes: list[OSMNode], flinger: Flinger
) -> tuple[np.ndarray, np.ndarray]:
    """
    Get geometric center of nodes set.

    :param nodes: node list
    :param flinger: flinger that remap geo positions
    """
    boundary: list[MinMax] = [MinMax(), MinMax()]

    for node in nodes:
        boundary[0].update(node.coordinates[0])
        boundary[1].update(node.coordinates[1])
    center_coordinates: np.ndarray = np.array(
        (boundary[0].center(), boundary[1].center())
    )
    return flinger.fling(center_coordinates), center_coordinates


def get_user_color(text: str, seed: str) -> Color:
    """Generate random color based on text."""
    if text == "":
        return Color("black")
    return Color("#" + sha256((seed + text).encode("utf-8")).hexdigest()[-6:])


def get_time_color(time: Optional[datetime], boundaries: MinMax) -> Color:
    """
    Generate color based on time.

    :param time: current element creation time
    :param boundaries: minimum and maximum element creation time on the map
    """
    return get_gradient_color(
        time if time else boundaries.max_, boundaries, TIME_COLOR_SCALE
    )


def glue(ways: list[OSMWay]) -> list[list[OSMNode]]:
    """
    Try to glue ways that share nodes.

    :param ways: ways to glue
    """
    result: list[list[OSMNode]] = []
    to_process: set[tuple[OSMNode]] = set()

    for way in ways:
        if way.is_cycle():
            result.append(way.nodes)
        else:
            to_process.add(tuple(way.nodes))

    while to_process:
        nodes: list[OSMNode] = list(to_process.pop())
        glued: Optional[list[OSMNode]] = None
        other_nodes: Optional[tuple[OSMNode]] = None

        for other_nodes in to_process:
            glued = try_to_glue(nodes, list(other_nodes))
            if glued is not None:
                break

        if glued is not None:
            to_process.remove(other_nodes)
            if is_cycle(glued):
                result.append(glued)
            else:
                to_process.add(tuple(glued))
        else:
            result.append(nodes)

    return result


def is_cycle(nodes: list[OSMNode]) -> bool:
    """Is way a cycle way or an area boundary."""
    return nodes[0] == nodes[-1]


def try_to_glue(
    nodes: list[OSMNode], other: list[OSMNode]
) -> Optional[list[OSMNode]]:
    """Create new combined way if ways share endpoints."""
    if nodes[0] == other[0]:
        return list(reversed(other[1:])) + nodes
    if nodes[0] == other[-1]:
        return other[:-1] + nodes
    if nodes[-1] == other[-1]:
        return nodes + list(reversed(other[:-1]))
    if nodes[-1] == other[0]:
        return nodes + other[1:]
    return None


class Constructor:
    """Map Machine node and way constructor."""

    def __init__(
        self,
        osm_data: OSMData,
        flinger: Flinger,
        extractor: ShapeExtractor,
        configuration: MapConfiguration,
    ) -> None:
        self.osm_data: OSMData = osm_data
        self.flinger: Flinger = flinger
        self.scheme: Scheme = configuration.scheme
        self.extractor: ShapeExtractor = extractor
        self.configuration: MapConfiguration = configuration
        self.text_constructor: TextConstructor = TextConstructor(self.scheme)

        if self.configuration.level == "all":
            self.check_level = lambda x: True
        elif self.configuration.level == "overground":
            self.check_level = check_level_overground
        elif self.configuration.level == "underground":
            self.check_level = lambda x: not check_level_overground(x)
        else:
            self.check_level = lambda x: check_level_number(
                x, float(self.configuration.level)
            )

        self.points: list[Point] = []
        self.figures: list[StyledFigure] = []
        self.buildings: list[Building] = []
        self.roads: Roads = Roads()
        self.trees: list[Tree] = []
        self.craters: list[Crater] = []
        self.direction_sectors: list[DirectionSector] = []

        self.heights: set[float] = {0.25 / BUILDING_SCALE, 0.5 / BUILDING_SCALE}

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
        """Construct Map Machine ways."""
        logging.info("Constructing ways...")
        for way_id in self.osm_data.ways:
            way: OSMWay = self.osm_data.ways[way_id]
            self.construct_line(way, [], [way.nodes])

    def construct_line(
        self,
        line: Union[OSMWay, OSMRelation],
        inners: list[list[OSMNode]],
        outers: list[list[OSMNode]],
    ) -> None:
        """
        Construct way or relation.

        :param line: OpenStreetMap way or relation
        :param inners: list of polygons that compose inner boundary
        :param outers: list of polygons that compose outer boundary
        """
        assert len(outers) >= 1

        if len(outers[0]) == 0:
            return

        if not self.check_level(line.tags):
            return

        center_point, _ = line_center(outers[0], self.flinger)
        if self.configuration.is_wireframe():
            # Dead code to make insensitive static analysis happy.
            color: Color = self.scheme.get_default_color()

            if self.configuration.drawing_mode == DrawingMode.AUTHOR:
                color = get_user_color(
                    line.user if line.user else "", self.configuration.seed
                )
            elif self.configuration.drawing_mode == DrawingMode.TIME:
                color = get_time_color(line.timestamp, self.osm_data.time)
            elif self.configuration.drawing_mode == DrawingMode.WHITE:
                color = Color("#666666")
            elif self.configuration.drawing_mode == DrawingMode.BLACK:
                color = Color("#BBBBBB")
            elif self.configuration.drawing_mode != DrawingMode.NORMAL:
                logging.fatal(
                    f"Drawing mode {self.configuration.drawing_mode} is not "
                    f"supported."
                )
                sys.exit(1)
            self.draw_special_mode(line, inners, outers, color)
            return

        if not line.tags:
            return

        building_mode: BuildingMode = self.configuration.building_mode
        if "building" in line.tags or (
            building_mode == BuildingMode.ISOMETRIC
            and "building:part" in line.tags
        ):
            self.add_building(
                Building(line.tags, inners, outers, self.flinger, self.scheme)
            )

        road_matcher: RoadMatcher = self.scheme.get_road(line.tags)
        if road_matcher:
            road: Road = Road(
                line.tags, outers[0], road_matcher, self.flinger, self.scheme
            )
            self.roads.append(road)
            return

        processed: set[str] = set()

        recolor: Optional[Color] = None

        if line.tags.get("railway") == "subway":
            for color_tag_key in ["color", "colour"]:
                if color_tag_key in line.tags:
                    recolor = self.scheme.get_color(line.tags[color_tag_key])
                    processed.add(color_tag_key)

        line_styles: list[LineStyle] = self.scheme.get_style(line.tags)

        for line_style in line_styles:
            if recolor is not None:
                new_style: dict[str, Union[float, int, str]] = dict(
                    line_style.style
                )
                new_style["stroke"] = recolor.hex
                line_style = LineStyle(
                    new_style, line_style.parallel_offset, line_style.priority
                )

            self.figures.append(
                StyledFigure(line.tags, inners, outers, line_style)
            )
            if not (
                line.get_tag("area") == "yes"
                or line.get_tag("type") == "multipolygon"
                or is_cycle(outers[0])
                and line.get_tag("area") != "no"
                and self.scheme.is_area(line.tags)
            ):
                continue

            priority: int
            icon_set: IconSet
            icon_set, priority = self.configuration.get_icon(
                self.extractor, line.tags, processed
            )
            if icon_set is not None:
                labels: list[Label] = self.text_constructor.construct_text(
                    line.tags,
                    processed,
                    self.configuration.label_mode,
                )
                point: Point = Point(
                    icon_set,
                    labels,
                    line.tags,
                    processed,
                    center_point,
                    is_for_node=False,
                    priority=priority,
                    add_tooltips=self.configuration.show_tooltips,
                )
                self.points.append(point)

        # TODO: probably we may want to skip the next part if `line_styles`
        # are not empty.
        self.add_point_for_line(center_point, inners, line, outers)

    def add_point_for_line(self, center_point, inners, line, outers) -> None:
        """Add icon at the center point of the way or relation."""
        if DEBUG:
            style: dict[str, Any] = {
                "fill": "none",
                "stroke": Color("red").hex,
                "stroke-width": 1.0,
            }
            figure: StyledFigure = StyledFigure(
                line.tags, inners, outers, LineStyle(style, 0.0, 1000.0)
            )
            self.figures.append(figure)

        processed: set[str] = set()
        priority: int
        icon_set: IconSet
        icon_set, priority = self.configuration.get_icon(
            self.extractor, line.tags, processed
        )
        if icon_set is not None:
            labels: list[Label] = self.text_constructor.construct_text(
                line.tags, processed, self.configuration.label_mode
            )
            point: Point = Point(
                icon_set,
                labels,
                line.tags,
                processed,
                center_point,
                is_for_node=False,
                priority=priority,
                add_tooltips=self.configuration.show_tooltips,
            )
            self.points.append(point)

    def draw_special_mode(
        self,
        line: Union[OSMWay, OSMRelation],
        inners: list[list[OSMNode]],
        outers: list[list[OSMNode]],
        color: Color,
    ) -> None:
        """Add figure for special mode: time or author."""
        style: dict[str, Any] = {
            "fill": "none",
            "stroke": color.hex,
            "stroke-width": 1,
        }
        self.figures.append(
            StyledFigure(line.tags, inners, outers, LineStyle(style))
        )

    def construct_relations(self) -> None:
        """Construct Map Machine ways from OSM relations."""
        for relation_id in self.osm_data.relations:
            relation: OSMRelation = self.osm_data.relations[relation_id]
            tags: dict[str, str] = relation.tags
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
        """Construct point and add them to the collection."""
        logging.info("Constructing nodes...")

        # Sort node vertically (using latitude values) to draw them from top to
        # bottom.
        sorted_node_ids: Iterator[int] = sorted(
            self.osm_data.nodes.keys(),
            key=lambda x: -self.osm_data.nodes[x].coordinates[0],
        )
        for node_id in sorted_node_ids:
            self.construct_node(self.osm_data.nodes[node_id])

    def construct_node(self, node: OSMNode) -> None:
        """Create new point if needed and add it to the point collection."""
        tags: dict[str, str] = node.tags

        if not tags:
            return
        if not self.check_level(tags):
            return

        processed: set[str] = set()

        flung: np.ndarray = self.flinger.fling(node.coordinates)

        priority: int
        icon_set: IconSet
        draw_outline: bool = True

        if self.configuration.drawing_mode in (
            DrawingMode.AUTHOR,
            DrawingMode.TIME,
        ):
            # Dead code to make insensitive static analysis happy.
            color: Color = self.scheme.get_default_color()

            if self.configuration.drawing_mode == DrawingMode.AUTHOR:
                color = get_user_color(node.user, self.configuration.seed)
            if self.configuration.drawing_mode == DrawingMode.TIME:
                color = get_time_color(node.timestamp, self.osm_data.time)

            dot: Shape = self.extractor.get_shape(DEFAULT_SMALL_SHAPE_ID)
            icon_set: IconSet = IconSet(
                Icon([ShapeSpecification(dot, color)]),
                [],
                Icon([ShapeSpecification(dot, color)]),
                set(),
            )
            point: Point = Point(
                icon_set,
                [],
                tags,
                processed,
                flung,
                draw_outline=False,
                add_tooltips=self.configuration.show_tooltips,
            )
            self.points.append(point)
            return

        if self.configuration.drawing_mode in (
            DrawingMode.WHITE,
            DrawingMode.BLACK,
        ):
            # Dead code to make insensitive static analysis happy.
            color: Color = self.scheme.get_default_color()

            if self.configuration.drawing_mode == DrawingMode.WHITE:
                color = Color("#CCCCCC")
            if self.configuration.drawing_mode == DrawingMode.BLACK:
                color = Color("#444444")
            icon_set, priority = self.configuration.get_icon(
                self.extractor, tags, processed
            )
            icon_set.main_icon.recolor(color)
            point: Point = Point(
                icon_set,
                [],
                tags,
                processed,
                flung,
                add_tooltips=self.configuration.show_tooltips,
            )
            self.points.append(point)
            return

        icon_set, priority = self.configuration.get_icon(
            self.extractor, tags, processed
        )
        if icon_set is None:
            return

        labels: list[Label] = self.text_constructor.construct_text(
            tags, processed, self.configuration.label_mode
        )
        self.scheme.process_ignored(tags, processed)

        if node.get_tag("natural") == "tree" and (
            "diameter_crown" in node.tags or "circumference" in node.tags
        ):
            self.trees.append(Tree(tags, node.coordinates, flung))
            return

        if node.get_tag("natural") == "crater" and "diameter" in node.tags:
            self.craters.append(Crater(tags, node.coordinates, flung))
            return

        if "direction" in node.tags or "camera:direction" in node.tags:
            self.direction_sectors.append(DirectionSector(tags, flung))
        point: Point = Point(
            icon_set,
            labels,
            tags,
            processed,
            flung,
            priority=priority,
            draw_outline=draw_outline,
            add_tooltips=self.configuration.show_tooltips,
        )
        self.points.append(point)

    def get_sorted_figures(self) -> list[StyledFigure]:
        """Get all figures sorted by priority."""
        return sorted(self.figures)


def check_level_number(tags: Tags, level: float) -> bool:
    """Check if element described by tags is no the specified level."""
    if "level" in tags:
        if level not in parse_levels(tags["level"]):
            return False
    else:
        return False
    return True


def check_level_overground(tags: Tags) -> bool:
    """Check if element described by tags is overground."""
    if "level" in tags:
        try:
            for level in map(float, tags["level"].replace(",", ".").split(";")):
                if level < 0.0:
                    return False
        except ValueError:
            pass

    return (
        tags.get("location") != "underground"
        and tags.get("parking") != "underground"
        and tags.get("tunnel") != "yes"
    )
