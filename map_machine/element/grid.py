import logging
from pathlib import Path

import numpy as np
from svgwrite import Drawing
from svgwrite.text import Text

from map_machine.constructor import Constructor
from map_machine.geometry.boundary_box import BoundaryBox
from map_machine.geometry.flinger import Flinger
from map_machine.map_configuration import MapConfiguration
from map_machine.mapper import Map
from map_machine.osm.osm_reader import (
    OSMNode,
    OSMData,
    Tags,
    OSMWay,
    OSMMember,
    OSMRelation,
)
from map_machine.pictogram.icon import ShapeExtractor
from map_machine.scheme import Scheme
from map_machine.workspace import Workspace

workspace: Workspace = Workspace(Path("temp"))

SCHEME: Scheme = Scheme.from_file(workspace.DEFAULT_SCHEME_PATH)
SHAPE_EXTRACTOR: ShapeExtractor = ShapeExtractor(
    workspace.ICONS_PATH, workspace.ICONS_CONFIG_PATH
)
DEFAULT_ZOOM: float = 18.0


class Grid:
    """Creating map with elements ordered in grid."""

    def __init__(self, x_step: float = 0.0002, y_step: float = 0.0003):
        self.x_step: float = x_step
        self.y_step: float = y_step

        self.index: int = 0
        self.nodes: dict[OSMNode, tuple[int, int]] = {}

        self.max_j: float = 0
        self.max_i: float = 0

        self.way_id: int = 0
        self.relation_id: int = 0

        self.osm_data: OSMData = OSMData()
        self.texts: list[tuple[str, int, int]] = []

    def add_node(self, tags: Tags, i: int, j: int) -> OSMNode:
        """Add OSM node to the grid."""
        self.index += 1
        node: OSMNode = OSMNode(
            tags,
            self.index,
            np.array((-i * self.y_step, j * self.x_step)),
        )
        self.nodes[node] = (j, i)
        self.osm_data.add_node(node)
        self.max_j = max(self.max_j, j * self.x_step)
        self.max_i = max(self.max_i, i * self.y_step)
        return node

    def add_way(self, tags: Tags, nodes: list[OSMNode]) -> OSMWay:
        """Add OSM way to the grid."""
        osm_way: OSMWay = OSMWay(tags, self.way_id, nodes)
        self.osm_data.add_way(osm_way)
        self.way_id += 1
        return osm_way

    def add_relation(self, tags: Tags, members: list[OSMMember]) -> OSMRelation:
        """Connect objects on the gird with relations."""
        osm_relation: OSMRelation = OSMRelation(tags, self.relation_id, members)
        self.osm_data.add_relation(osm_relation)
        self.relation_id += 1
        return osm_relation

    def add_text(self, text: str, i: int, j: int) -> None:
        """Add simple text label to the grid."""
        self.texts.append((text, i, j))

    def get_boundary_box(self) -> BoundaryBox:
        """Compute resulting boundary box with margin of one grid step."""
        return BoundaryBox(
            -self.x_step * 1.5,
            -self.max_i - self.y_step * 1.5,
            self.max_j + self.x_step * 1.5,
            self.y_step * 1.5,
        )

    def draw(self, output_path: Path, zoom: float = DEFAULT_ZOOM) -> None:
        """Draw grid."""
        configuration: MapConfiguration = MapConfiguration(
            SCHEME, level="all", credit=None
        )
        flinger: Flinger = Flinger(
            self.get_boundary_box(), zoom, self.osm_data.equator_length
        )
        svg: Drawing = Drawing(output_path.name, flinger.size)
        constructor: Constructor = Constructor(
            self.osm_data, flinger, SHAPE_EXTRACTOR, configuration
        )
        constructor.construct()
        map_: Map = Map(flinger, svg, configuration)
        map_.draw(constructor)

        for text, i, j in self.texts:
            svg.add(
                Text(
                    text,
                    flinger.fling((-i * self.y_step, j * self.x_step)) + (0, 3),
                    font_family="JetBrains Mono",
                    font_size=12,
                )
            )

        with output_path.open("w") as output_file:
            svg.write(output_file)
            logging.info(f"Map is drawn to {output_path}.")
