import logging
from pathlib import Path

import numpy as np
from svgwrite import Drawing
from svgwrite.text import Text

from map_machine.constructor import Constructor
from map_machine.geometry.flinger import Flinger, TranslateFlinger
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

    def __init__(
        self,
        x_step: float = 20.0,
        y_step: float = 20.0,
        show_credit: bool = True,
        margin: float = 1.5,
    ) -> None:
        self.x_step: float = x_step
        self.y_step: float = y_step
        self.show_credit: bool = show_credit
        self.margin: float = margin

        self.index: int = 0
        self.nodes: dict[OSMNode, tuple[int, int]] = {}

        self.max_j: float = 0.0
        self.max_i: float = 0.0

        self.way_id: int = 0
        self.relation_id: int = 0

        self.osm_data: OSMData = OSMData()
        self.texts: list[tuple[str, int, int]] = []

    def add_node(self, tags: Tags, i: int, j: int) -> OSMNode:
        """Add OSM node to the grid."""
        self.index += 1
        node: OSMNode = OSMNode(tags, self.index, np.array((i, j)))
        self.nodes[node] = (j, i)
        self.osm_data.add_node(node)
        self.max_j = max(self.max_j, j)
        self.max_i = max(self.max_i, i)
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

    def draw(self, output_path: Path) -> None:
        """Draw grid."""
        configuration: MapConfiguration = MapConfiguration(
            SCHEME,
            level="all",
            credit=None,
            show_credit=self.show_credit,
            zoom_level=19.0,
        )
        size: np.ndarray = np.array(
            (
                (self.max_i + self.margin * 2.0) * self.x_step,
                (self.max_j + self.margin * 2.0) * self.y_step,
            )
        )

        flinger: Flinger = TranslateFlinger(
            size,
            np.array((self.x_step, self.y_step)),
            np.array((self.margin, self.margin)),
        )
        svg: Drawing = Drawing(output_path.name, size)
        constructor: Constructor = Constructor(
            self.osm_data, flinger, SHAPE_EXTRACTOR, configuration
        )
        constructor.construct()
        map_: Map = Map(flinger, svg, configuration)
        map_.draw(constructor)

        for text, i, j in self.texts:
            text_element: Text = Text(
                text,
                flinger.fling((i, j)) + np.array((0, 3)),
                font_family="JetBrains Mono",
                font_size=12,
            )
            svg.add(text_element)

        with output_path.open("w") as output_file:
            svg.write(output_file)
            logging.info(f"Map is drawn to {output_path}.")
