"""
Simple OpenStreetMap renderer.
"""
import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set

import numpy as np
import svgwrite
from colour import Color
from svgwrite.container import Group
from svgwrite.path import Path as SVGPath
from svgwrite.shapes import Rect

from map_machine.constructor import Constructor
from map_machine.drawing import draw_text
from map_machine.feature.building import Building, draw_walls, BUILDING_SCALE
from map_machine.feature.road import Intersection, Road, RoadPart
from map_machine.geometry.boundary_box import BoundaryBox
from map_machine.geometry.flinger import Flinger
from map_machine.geometry.vector import Segment
from map_machine.map_configuration import LabelMode, MapConfiguration
from map_machine.osm.osm_getter import NetworkError, get_osm
from map_machine.osm.osm_reader import OSMData, OSMNode
from map_machine.pictogram.icon import ShapeExtractor
from map_machine.pictogram.point import Occupied, Point
from map_machine.scheme import Scheme
from map_machine.ui.cli import BuildingMode
from map_machine.workspace import workspace

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


class Map:
    """Map drawing."""

    def __init__(
        self,
        flinger: Flinger,
        svg: svgwrite.Drawing,
        scheme: Scheme,
        configuration: MapConfiguration,
    ) -> None:
        self.flinger: Flinger = flinger
        self.svg: svgwrite.Drawing = svg
        self.scheme: Scheme = scheme
        self.configuration = configuration

        self.background_color: Color = self.scheme.get_color("background_color")
        if color := self.configuration.background_color():
            self.background_color = color

    def draw(self, constructor: Constructor) -> None:
        """Draw map."""
        self.svg.add(
            Rect((0.0, 0.0), self.flinger.size, fill=self.background_color)
        )
        logging.info("Drawing ways...")

        for figure in constructor.get_sorted_figures():
            path_commands: str = figure.get_path(self.flinger)
            if path_commands:
                path: SVGPath = SVGPath(d=path_commands)
                path.update(figure.line_style.style)
                self.svg.add(path)

        constructor.roads.draw(self.svg, self.flinger)

        for tree in constructor.trees:
            tree.draw(self.svg, self.flinger, self.scheme)
        for crater in constructor.craters:
            crater.draw(self.svg, self.flinger)

        self.draw_buildings(constructor)

        for direction_sector in constructor.direction_sectors:
            direction_sector.draw(self.svg, self.scheme)

        # All other points

        occupied: Optional[Occupied]
        if self.configuration.overlap == 0:
            occupied = None
        else:
            occupied = Occupied(
                self.flinger.size[0],
                self.flinger.size[1],
                self.configuration.overlap,
            )

        nodes: List[Point] = sorted(
            constructor.points, key=lambda x: -x.priority
        )
        logging.info("Drawing main icons...")
        for node in nodes:
            node.draw_main_shapes(self.svg, occupied)

        logging.info("Drawing extra icons...")
        for point in nodes:
            point.draw_extra_shapes(self.svg, occupied)

        logging.info("Drawing texts...")
        for point in nodes:
            if (
                not self.configuration.is_wireframe()
                and self.configuration.label_mode != LabelMode.NO
            ):
                point.draw_texts(
                    self.svg, occupied, self.configuration.label_mode
                )

        self.draw_credits(constructor.flinger.size)

    def draw_buildings(self, constructor: Constructor) -> None:
        """Draw buildings: shade, walls, and roof."""
        if self.configuration.building_mode == BuildingMode.NO:
            return
        if self.configuration.building_mode == BuildingMode.FLAT:
            for building in constructor.buildings:
                building.draw(self.svg, self.flinger)
            return

        logging.info("Drawing buildings...")

        scale: float = self.flinger.get_scale()
        building_shade: Group = Group(opacity=0.1)
        for building in constructor.buildings:
            building.draw_shade(building_shade, self.flinger)
        self.svg.add(building_shade)

        walls: Dict[Segment, Building] = {}

        for building in constructor.buildings:
            for part in building.parts:
                walls[part] = building

        sorted_walls = sorted(walls.keys())

        previous_height: float = 0.0
        for height in sorted(constructor.heights):
            shift_1: np.ndarray = np.array(
                (0.0, -previous_height * scale * BUILDING_SCALE)
            )
            shift_2: np.ndarray = np.array(
                (0.0, -height * scale * BUILDING_SCALE)
            )
            for wall in sorted_walls:
                building: Building = walls[wall]
                if building.height < height or building.min_height >= height:
                    continue

                draw_walls(self.svg, building, wall, height, shift_1, shift_2)

            if self.configuration.draw_roofs:
                for building in constructor.buildings:
                    if building.height == height:
                        building.draw_roof(self.svg, self.flinger, scale)

            previous_height = height

    def draw_simple_roads(self, roads: Iterator[Road]) -> None:
        """Draw road as simple SVG path."""
        nodes: Dict[OSMNode, Set[RoadPart]] = {}

        for road in roads:
            for index in range(len(road.nodes) - 1):
                node_1: OSMNode = road.nodes[index]
                node_2: OSMNode = road.nodes[index + 1]
                point_1: np.ndarray = self.flinger.fling(node_1.coordinates)
                point_2: np.ndarray = self.flinger.fling(node_2.coordinates)
                scale: float = self.flinger.get_scale(node_1.coordinates)
                part_1: RoadPart = RoadPart(point_1, point_2, road.lanes, scale)
                part_2: RoadPart = RoadPart(point_2, point_1, road.lanes, scale)
                # part_1.draw_normal(self.svg)

                for node in node_1, node_2:
                    if node not in nodes:
                        nodes[node] = set()

                nodes[node_1].add(part_1)
                nodes[node_2].add(part_2)

        for node, parts in nodes.items():
            if len(parts) < 4:
                continue
            intersection: Intersection = Intersection(list(parts))
            intersection.draw(self.svg, True)

    def draw_credits(self, size: np.ndarray):

        for text, point in (
            ("Data: © OpenStreetMap contributors", np.array((15, 27))),
            ("Rendering: Map Machine", np.array((15, 15))),
        ):
            for stroke_width, stroke, opacity in (
                (3.0, Color("white"), 0.7),
                (1.0, None, 1.0),
            ):
                draw_text(
                    self.svg,
                    text,
                    size - point,
                    10,
                    Color("#888888"),
                    anchor="end",
                    stroke_width=stroke_width,
                    stroke=stroke,
                    opacity=opacity,
                )


def fatal(message: str) -> None:
    logging.fatal(message)
    sys.exit(1)


def render_map(arguments: argparse.Namespace) -> None:
    """
    Map rendering entry point.

    :param arguments: command-line arguments
    """
    configuration: MapConfiguration = MapConfiguration.from_options(
        arguments, float(arguments.zoom)
    )
    cache_path: Path = Path(arguments.cache)
    cache_path.mkdir(parents=True, exist_ok=True)

    # Compute boundary box

    boundary_box: Optional[BoundaryBox] = None

    if arguments.boundary_box:
        boundary_box = BoundaryBox.from_text(arguments.boundary_box)
    elif arguments.coordinates and arguments.size:
        coordinates: np.ndarray = np.array(
            list(map(float, arguments.coordinates.split(",")))
        )
        if len(coordinates) != 2:
            fatal("Wrong number of coordinates.")
        width, height = np.array(list(map(float, arguments.size.split(","))))
        boundary_box = BoundaryBox.from_coordinates(
            coordinates, configuration.zoom_level, width, height
        )

    # Determine files

    if arguments.input_file_names:
        input_file_names = list(map(Path, arguments.input_file_names))
    elif boundary_box:
        try:
            cache_file_path: Path = (
                cache_path / f"{boundary_box.get_format()}.osm"
            )
            get_osm(boundary_box, cache_file_path)
            input_file_names = [cache_file_path]
        except NetworkError as error:
            logging.fatal(error.message)
            sys.exit(1)
    else:
        fatal(
            "Specify either --input, or --boundary-box, or --coordinates and "
            "--size."
        )

    # Get OpenStreetMap data

    osm_data: OSMData = OSMData()
    for input_file_name in input_file_names:
        if not input_file_name.is_file():
            logging.fatal(f"No such file: {input_file_name}.")
            sys.exit(1)

        if input_file_name.name.endswith(".json"):
            osm_data.parse_overpass(input_file_name)
        else:
            osm_data.parse_osm_file(input_file_name)

    if not boundary_box:
        boundary_box = osm_data.view_box
    if not boundary_box:
        boundary_box = osm_data.boundary_box

    # Render

    flinger: Flinger = Flinger(
        boundary_box, arguments.zoom, osm_data.equator_length
    )
    size: np.ndarray = flinger.size

    svg: svgwrite.Drawing = svgwrite.Drawing(arguments.output_file_name, size)
    icon_extractor: ShapeExtractor = ShapeExtractor(
        workspace.ICONS_PATH, workspace.ICONS_CONFIG_PATH
    )

    scheme: Scheme = Scheme.from_file(workspace.DEFAULT_SCHEME_PATH)
    constructor: Constructor = Constructor(
        osm_data=osm_data,
        flinger=flinger,
        scheme=scheme,
        extractor=icon_extractor,
        configuration=configuration,
    )
    constructor.construct()

    map_: Map = Map(
        flinger=flinger, svg=svg, scheme=scheme, configuration=configuration
    )
    map_.draw(constructor)

    logging.info(f"Writing output SVG to {arguments.output_file_name}...")
    with open(arguments.output_file_name, "w", encoding="utf-8") as output_file:
        svg.write(output_file)
