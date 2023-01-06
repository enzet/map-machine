"""Simple OpenStreetMap renderer."""
import argparse
import logging
import sys
from pathlib import Path
from typing import Iterator, Optional

import numpy as np
import svgwrite
from colour import Color
from svgwrite.container import Group
from svgwrite.path import Path as SVGPath
from svgwrite.shapes import Rect

from map_machine import __project__
from map_machine.constructor import Constructor
from map_machine.drawing import draw_text
from map_machine.feature.building import Building, draw_walls, BUILDING_SCALE
from map_machine.feature.road import Intersection, Road, RoadPart
from map_machine.figure import StyledFigure
from map_machine.geometry.boundary_box import BoundaryBox
from map_machine.geometry.flinger import Flinger, MercatorFlinger
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

ROAD_PRIORITY: float = 40.0
DEFAULT_SIZE: tuple[float, float] = (800.0, 600.0)


class Map:
    """Map drawing."""

    def __init__(
        self,
        flinger: Flinger,
        svg: svgwrite.Drawing,
        configuration: MapConfiguration,
    ) -> None:
        self.flinger: Flinger = flinger
        self.svg: svgwrite.Drawing = svg
        self.scheme: Scheme = configuration.scheme
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

        figures: list[StyledFigure] = constructor.get_sorted_figures()

        top_figures: list[StyledFigure] = [
            x for x in figures if x.line_style.priority >= ROAD_PRIORITY
        ]
        bottom_figures: list[StyledFigure] = [
            x for x in figures if x.line_style.priority < ROAD_PRIORITY
        ]

        for figure in bottom_figures:
            path_commands: str = figure.get_path(self.flinger)

            if 'M' not in path_commands: # Deal with malformed paths
                continue
                
            if path_commands:
                path: SVGPath = SVGPath(d=path_commands)
                path.update(figure.line_style.style)
                self.svg.add(path)

        constructor.roads.draw(self.svg, self.flinger)

        for figure in top_figures:
            path_commands: str = figure.get_path(self.flinger)

            if 'M' not in path_commands: # Deal with malformed paths
                continue

            if path_commands:
                path: SVGPath = SVGPath(d=path_commands)
                path.update(figure.line_style.style)
                self.svg.add(path)

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

        nodes: list[Point] = sorted(
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

        if self.configuration.show_credit:
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

        walls: dict[Segment, Building] = {}

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
        nodes: dict[OSMNode, set[RoadPart]] = {}

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
        """
        Add OpenStreetMap credit and the link to the project itself.
        OpenStreetMap requires to use the credit “© OpenStreetMap contributors”.

        See https://www.openstreetmap.org/copyright
        """
        right_margin: float = 15.0
        bottom_margin: float = 15.0
        font_size: float = 10.0
        vertical_spacing: float = 2.0

        text_color: Color = Color("#888888")
        outline_color: Color = Color("#FFFFFF")

        credit_list: list[tuple[str, tuple[float, float]]] = [
            (f"Rendering: {__project__}", (right_margin, bottom_margin))
        ]
        if self.configuration.credit:
            data_credit: tuple[str, tuple[float, float]] = (
                f"Data: {self.configuration.credit}",
                (right_margin, bottom_margin + font_size + vertical_spacing),
            )
            credit_list.append(data_credit)

        for text, point in credit_list:
            for stroke_width, stroke, opacity in (
                (3.0, outline_color, 0.7),
                (1.0, None, 1.0),
            ):
                draw_text(
                    self.svg,
                    text,
                    size - np.array(point),
                    font_size,
                    text_color,
                    anchor="end",
                    stroke_width=stroke_width,
                    stroke=stroke,
                    opacity=opacity,
                )


def fatal(message: str) -> None:
    """Print error message and exit with non-zero exit code."""
    logging.fatal(message)
    sys.exit(1)


def render_map(arguments: argparse.Namespace) -> None:
    """
    Map rendering entry point.

    :param arguments: command-line arguments
    """
    scheme_path: Optional[Path] = workspace.find_scheme_path(arguments.scheme)
    if scheme_path is None:
        fatal(f"Scheme `{arguments.scheme}` not found.")

    scheme: Optional[Scheme] = Scheme.from_file(scheme_path)
    if scheme is None:
        fatal(f"Failed to load scheme from `{arguments.scheme}`.")

    configuration: MapConfiguration = MapConfiguration.from_options(
        scheme, arguments, float(arguments.zoom)
    )
    cache_path: Path = Path(arguments.cache)
    cache_path.mkdir(parents=True, exist_ok=True)

    # Compute boundary box.

    boundary_box: Optional[BoundaryBox] = None

    # If boundary box is specified explicitly, use it or stop the rendering
    # process if the box is invalid.
    if arguments.boundary_box:
        boundary_box = BoundaryBox.from_text(arguments.boundary_box)
        if not boundary_box:
            fatal("Invalid boundary box.")
        if arguments.coordinates:
            logging.warning(
                "Boundary box is explicitly specified. Coordinates are ignored."
            )

    elif arguments.coordinates:
        coordinates: Optional[np.ndarray] = None

        for delimiter in ",", "/":
            if delimiter in arguments.coordinates:
                coordinates = np.array(
                    list(map(float, arguments.coordinates.split(delimiter)))
                )

        if coordinates is None or len(coordinates) != 2:
            fatal("Wrong coordinates format.")

        if arguments.size:
            width, height = np.array(
                list(map(float, arguments.size.split(",")))
            )
        else:
            width, height = DEFAULT_SIZE

        boundary_box = BoundaryBox.from_coordinates(
            coordinates, configuration.zoom_level, width, height
        )

    # Determine files.

    input_file_names: Optional[list[Path]] = None
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
        fatal("Specify either --input, or --boundary-box, or --coordinates.")

    # Get OpenStreetMap data.

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

    # Render the map.

    flinger: MercatorFlinger = MercatorFlinger(
        boundary_box, arguments.zoom, osm_data.equator_length
    )
    size: np.ndarray = flinger.size

    svg: svgwrite.Drawing = svgwrite.Drawing(arguments.output_file_name, size)
    icon_extractor: ShapeExtractor = ShapeExtractor(
        workspace.ICONS_PATH, workspace.ICONS_CONFIG_PATH
    )

    constructor: Constructor = Constructor(
        osm_data=osm_data,
        flinger=flinger,
        extractor=icon_extractor,
        configuration=configuration,
    )
    constructor.construct()

    map_: Map = Map(flinger=flinger, svg=svg, configuration=configuration)
    map_.draw(constructor)

    logging.info(f"Writing output SVG to {arguments.output_file_name}...")
    with open(arguments.output_file_name, "w", encoding="utf-8") as output_file:
        svg.write(output_file)
