"""
Draw test nodes, ways, and relations.
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
from svgwrite import Drawing

from map_machine.constructor import Constructor
from map_machine.geometry.boundary_box import BoundaryBox
from map_machine.geometry.flinger import Flinger
from map_machine.map_configuration import MapConfiguration
from map_machine.mapper import Map
from map_machine.osm.osm_reader import OSMData, OSMNode, OSMWay
from map_machine.osm.tags import HIGHWAY_VALUES, AEROWAY_VALUES, RAILWAY_TAGS
from map_machine.pictogram.icon import ShapeExtractor
from map_machine.scheme import Scheme
from map_machine.workspace import Workspace

workspace: Workspace = Workspace(Path("temp"))

SCHEME: Scheme = Scheme.from_file(workspace.DEFAULT_SCHEME_PATH)
SHAPE_EXTRACTOR: ShapeExtractor = ShapeExtractor(
    workspace.ICONS_PATH, workspace.ICONS_CONFIG_PATH
)
DEFAULT_ZOOM: float = 18.0

ROAD_WIDTHS_AND_FEATURES: list[dict[str, str]] = [
    {"width": "4"},
    {"width": "8"},
    {"width": "12"},
    {"width": "16"},
    {"bridge": "yes", "width": "4"},
    {"bridge": "yes", "width": "8"},
    {"tunnel": "yes", "width": "4"},
    {"tunnel": "yes", "width": "8"},
    {"ford": "yes", "width": "4"},
    {"ford": "yes", "width": "8"},
    {"embankment": "yes", "width": "4"},
    {"embankment": "yes", "width": "8"},
]
ROAD_LANES_AND_FEATURES: list[dict[str, str]] = [
    {"lanes": "1"},
    {"lanes": "2"},
    {"lanes": "3"},
    {"lanes": "4"},
    {"bridge": "yes", "lanes": "1"},
    {"bridge": "yes", "lanes": "2"},
    {"tunnel": "yes", "lanes": "1"},
    {"tunnel": "yes", "lanes": "2"},
    {"ford": "yes", "lanes": "1"},
    {"ford": "yes", "lanes": "2"},
    {"embankment": "yes", "lanes": "1"},
    {"embankment": "yes", "lanes": "2"},
]


# See https://wiki.openstreetmap.org/wiki/Proposed_features/placement

PLACEMENT_FEATURES_1: list[dict[str, str]] = [
    {"lanes": "1"},
    {"lanes": "2", "placement": "middle_of:1"},
    {"lanes": "4", "placement": "middle_of:2"},
    {"placement": "transition"},
    {"lanes": "3", "placement": "right_of:1"},  # or placement=left_of:2
]
PLACEMENT_FEATURES_2: list[dict[str, str]] = [
    {"lanes": "2"},
    # or placement:backward=left_of:1
    {"lanes": "3", "placement:forward": "left_of:1"},
    {"lanes": "3", "placement": "transition"},
    {"lanes": "4", "placement:backward": "middle_of:1"},
    {"lanes": "3"},
]


@dataclass
class Grid:
    """Creating map with elements ordered in grid."""

    x_step: float = 0.0002
    y_step: float = 0.0003
    index: int = 0
    nodes: dict[OSMNode, tuple[int, int]] = field(default_factory=dict)
    max_j: float = 0
    max_i: float = 0

    def add_node(self, tags: dict[str, str], i: int, j: int) -> OSMNode:
        """Add OSM node to the grid."""
        self.index += 1
        node: OSMNode = OSMNode(
            tags,
            self.index,
            np.array((-i * self.y_step, j * self.x_step)),
        )
        self.nodes[node] = (j, i)
        self.max_j = max(self.max_j, j * self.x_step)
        self.max_i = max(self.max_i, i * self.y_step)
        return node

    def get_boundary_box(self) -> BoundaryBox:
        """Compute resulting boundary box with margin of one grid step."""
        return BoundaryBox(
            -self.x_step,
            -self.max_i - self.y_step,
            self.max_j + self.x_step,
            self.y_step,
        )


def draw_overlapped_ways(types: list[dict[str, str]], path: Path) -> None:
    """
    Draw two sets of ways intersecting each other to show how they overlapping.
    """
    osm_data: OSMData = OSMData()
    grid: Grid = Grid(0.00012, 0.00012)
    way_id: int = 0

    for i, type_1 in enumerate(types):
        node_1: OSMNode = grid.add_node({}, i + 1, 0)
        node_2: OSMNode = grid.add_node({}, i + 1, len(types) + 1)
        way: OSMWay = OSMWay(type_1, way_id, [node_1, node_2])
        way_id += 1
        osm_data.add_way(way)

    for i, type_1 in enumerate(types):
        node_1: OSMNode = grid.add_node({}, 0, i + 1)
        node_2: OSMNode = grid.add_node({}, len(types) + 1, i + 1)
        way: OSMWay = OSMWay(type_1, way_id, [node_1, node_2])
        way_id += 1
        osm_data.add_way(way)

    draw(osm_data, path, grid.get_boundary_box())


def draw_road_features(
    types: list[dict[str, str]], features: list[dict[str, str]], path: Path
) -> None:
    """Draw test image with different road features."""
    osm_data: OSMData = OSMData()
    grid: Grid = Grid()

    for i, type_ in enumerate(types):
        previous: Optional[OSMNode] = None

        for j in range(len(features) + 1):
            node: OSMNode = grid.add_node({}, i, j)

            if previous:
                tags: dict[str, str] = dict(type_)
                tags |= dict(features[j - 1])
                way: OSMWay = OSMWay(
                    tags, i * (len(features) + 1) + j, [previous, node]
                )
                osm_data.add_way(way)
            previous = node

    draw(osm_data, path, grid.get_boundary_box())


def draw(
    osm_data: OSMData,
    output_path: Path,
    boundary_box: BoundaryBox,
    zoom: float = DEFAULT_ZOOM,
) -> None:
    """Draw map."""
    configuration: MapConfiguration = MapConfiguration(level="all")

    flinger: Flinger = Flinger(boundary_box, zoom, osm_data.equator_length)
    svg: Drawing = Drawing(output_path.name, flinger.size)
    constructor: Constructor = Constructor(
        osm_data, flinger, SCHEME, SHAPE_EXTRACTOR, configuration
    )
    constructor.construct()
    map_: Map = Map(flinger, svg, SCHEME, configuration)
    map_.draw(constructor)

    with output_path.open("w") as output_file:
        svg.write(output_file)
        logging.info(f"Map is drawn to {output_path}.")


if __name__ == "__main__":
    logging.basicConfig(format="%(levelname)s %(message)s", level=logging.INFO)

    out_path: Path = Path("out")

    highway_tags: list[dict[str, str]] = [
        {"highway": value} for value in HIGHWAY_VALUES
    ]
    aeroway_tags: list[dict[str, str]] = [
        {"aeroway": value} for value in AEROWAY_VALUES
    ]

    draw_road_features(
        highway_tags, ROAD_LANES_AND_FEATURES, out_path / "lanes.svg"
    )
    draw_road_features(
        highway_tags + RAILWAY_TAGS + aeroway_tags,
        ROAD_WIDTHS_AND_FEATURES,
        out_path / "width.svg",
    )
    draw_road_features(
        highway_tags,
        PLACEMENT_FEATURES_1 + [{"highway": "none"}] + PLACEMENT_FEATURES_2,
        out_path / "placement.svg",
    )
    draw_overlapped_ways(highway_tags, out_path / "overlap.svg")
