"""
Simple OpenStreetMap renderer.
"""
import argparse
import logging
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set

import numpy as np
import svgwrite
from colour import Color
from svgwrite.container import Group
from svgwrite.path import Path as SVGPath
from svgwrite.shapes import Rect

from map_machine.boundary_box import BoundaryBox
from map_machine.constructor import Constructor
from map_machine.figure import StyledFigure
from map_machine.flinger import Flinger
from map_machine.icon import ShapeExtractor
from map_machine.map_configuration import LabelMode, MapConfiguration
from map_machine.osm_getter import NetworkError, get_osm
from map_machine.osm_reader import OSMData, OSMNode
from map_machine.point import Occupied, Point
from map_machine.road import Intersection, Road, RoadPart
from map_machine.scheme import Scheme
from map_machine.ui import BuildingMode, progress_bar
from map_machine.workspace import workspace

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
        configuration: MapConfiguration,
    ) -> None:
        self.flinger: Flinger = flinger
        self.svg: svgwrite.Drawing = svg
        self.scheme: Scheme = scheme
        self.configuration = configuration

        self.background_color: Color = self.scheme.get_color("background_color")
        if self.configuration.is_wireframe():
            self.background_color: Color = Color("#111111")

    def draw(self, constructor: Constructor) -> None:
        """Draw map."""
        self.svg.add(
            Rect((0, 0), self.flinger.size, fill=self.background_color)
        )
        ways: List[StyledFigure] = sorted(
            constructor.figures, key=lambda x: x.line_style.priority
        )
        ways_length: int = len(ways)
        for index, way in enumerate(ways):
            progress_bar(index, ways_length, step=10, text="Drawing ways")
            path_commands: str = way.get_path(self.flinger)
            if path_commands:
                path: SVGPath = SVGPath(d=path_commands)
                path.update(way.line_style.style)
                self.svg.add(path)
        progress_bar(-1, 0, text="Drawing ways")

        constructor.roads.draw(self.svg, self.flinger)

        for tree in constructor.trees:
            tree.draw(self.svg, self.flinger, self.scheme)
        for tree in constructor.craters:
            tree.draw(self.svg, self.flinger)

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
        steps: int = len(nodes)

        for index, node in enumerate(nodes):
            progress_bar(index, steps * 3, step=10, text="Drawing main icons")
            node.draw_main_shapes(self.svg, occupied)

        for index, point in enumerate(nodes):
            progress_bar(
                steps + index, steps * 3, step=10, text="Drawing extra icons"
            )
            point.draw_extra_shapes(self.svg, occupied)

        for index, point in enumerate(nodes):
            progress_bar(
                steps * 2 + index, steps * 3, step=10, text="Drawing texts"
            )
            if (
                not self.configuration.is_wireframe()
                and self.configuration.label_mode != LabelMode.NO
            ):
                point.draw_texts(
                    self.svg, occupied, self.configuration.label_mode
                )

        progress_bar(-1, len(nodes), step=10, text="Drawing nodes")

    def draw_buildings(self, constructor: Constructor) -> None:
        """Draw buildings: shade, walls, and roof."""
        if self.configuration.building_mode == BuildingMode.FLAT:
            for building in constructor.buildings:
                building.draw(self.svg, self.flinger)
            return

        scale: float = self.flinger.get_scale() / 3.0
        building_shade: Group = Group(opacity=0.1)
        for building in constructor.buildings:
            building.draw_shade(building_shade, self.flinger)
        self.svg.add(building_shade)

        previous_height: float = 0
        count: int = len(constructor.heights)
        for index, height in enumerate(sorted(constructor.heights)):
            progress_bar(index, count, step=1, text="Drawing buildings")
            fill: Color()
            for building in constructor.buildings:
                if building.height < height or building.min_height > height:
                    continue
                building.draw_walls(self.svg, height, previous_height, scale)

            for building in constructor.buildings:
                if building.height == height:
                    building.draw_roof(self.svg, self.flinger, scale)

            previous_height = height

        progress_bar(-1, count, step=1, text="Drawing buildings")

    def draw_roads(self, roads: Iterator[Road]) -> None:
        """Draw road as simple SVG path."""
        nodes: Dict[OSMNode, Set[RoadPart]] = {}

        for road in roads:
            for index in range(len(road.outers[0]) - 1):
                node_1: OSMNode = road.outers[0][index]
                node_2: OSMNode = road.outers[0][index + 1]
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

        for node in nodes:
            parts: Set[RoadPart] = nodes[node]
            if len(parts) < 4:
                continue
            intersection: Intersection = Intersection(list(parts))
            intersection.draw(self.svg, True)


def ui(arguments: argparse.Namespace) -> None:
    """
    Map Machine entry point.

    :param arguments: command-line arguments
    """
    configuration: MapConfiguration = MapConfiguration.from_options(
        arguments, int(arguments.zoom)
    )
    cache_path: Path = Path(arguments.cache)
    cache_path.mkdir(parents=True, exist_ok=True)

    boundary_box: Optional[BoundaryBox] = None
    input_file_names: List[Path] = []

    if arguments.input_file_names:
        input_file_names = list(map(Path, arguments.input_file_names))
        if arguments.boundary_box:
            boundary_box = BoundaryBox.from_text(arguments.boundary_box)
    else:
        if arguments.boundary_box:
            boundary_box = BoundaryBox.from_text(arguments.boundary_box)
        elif arguments.coordinates and arguments.size:
            coordinates: np.ndarray = np.array(
                list(map(float, arguments.coordinates.split(",")))
            )
            width, height = np.array(
                list(map(float, arguments.size.split(",")))
            )
            boundary_box = BoundaryBox.from_coordinates(
                coordinates, configuration.zoom_level, width, height
            )
        else:
            logging.fatal(
                "Specify either --input, or --boundary-box, or --coordinates "
                "and --size."
            )
            exit(1)

        try:
            cache_file_path: Path = (
                cache_path / f"{boundary_box.get_format()}.osm"
            )
            get_osm(boundary_box, cache_file_path)
            input_file_names = [cache_file_path]
        except NetworkError as e:
            logging.fatal(e.message)
            exit(1)

    scheme: Scheme = Scheme(workspace.DEFAULT_SCHEME_PATH)
    min_: np.ndarray
    max_: np.ndarray
    osm_data: OSMData

    osm_data: OSMData = OSMData()

    for input_file_name in input_file_names:
        if not input_file_name.is_file():
            logging.fatal(f"No such file: {input_file_name}.")
            exit(1)

        if input_file_name.name.endswith(".json"):
            osm_data.parse_overpass(input_file_name)
        else:
            osm_data.parse_osm_file(input_file_name)

    view_box: BoundaryBox = boundary_box if boundary_box else osm_data.view_box

    flinger: Flinger = Flinger(
        view_box, arguments.zoom, osm_data.equator_length
    )
    size: np.ndarray = flinger.size

    svg: svgwrite.Drawing = svgwrite.Drawing(
        arguments.output_file_name, size=size
    )
    icon_extractor: ShapeExtractor = ShapeExtractor(
        workspace.ICONS_PATH, workspace.ICONS_CONFIG_PATH
    )

    constructor: Constructor = Constructor(
        osm_data=osm_data,
        flinger=flinger,
        scheme=scheme,
        extractor=icon_extractor,
        configuration=configuration,
    )
    constructor.construct()

    painter: Map = Map(
        flinger=flinger, svg=svg, scheme=scheme, configuration=configuration
    )
    painter.draw(constructor)

    logging.info(f"Writing output SVG to {arguments.output_file_name}...")
    with open(arguments.output_file_name, "w") as output_file:
        svg.write(output_file)
