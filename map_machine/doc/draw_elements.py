"""
Draw test nodes, ways, and relations.
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from svgwrite import Drawing
from svgwrite.text import Text

from map_machine.constructor import Constructor
from map_machine.geometry.boundary_box import BoundaryBox
from map_machine.geometry.flinger import Flinger
from map_machine.map_configuration import MapConfiguration
from map_machine.mapper import Map
from map_machine.osm.osm_reader import OSMData, OSMNode, OSMWay, Tags
from map_machine.osm.tags import (
    HIGHWAY_VALUES,
    AEROWAY_VALUES,
    RAILWAY_VALUES,
    ROAD_VALUES,
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

ROAD_WIDTHS_AND_FEATURES: List[Dict[str, str]] = [
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
ROAD_LANES_AND_FEATURES: List[Dict[str, str]] = [
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

PLACEMENT_FEATURES_1: List[Dict[str, str]] = [
    {"lanes": "1"},
    {"lanes": "2", "placement": "middle_of:1"},
    {"lanes": "4", "placement": "middle_of:2"},
    {"placement": "transition"},
    {"lanes": "3", "placement": "right_of:1"},  # or placement=left_of:2
]
PLACEMENT_FEATURES_2: List[Dict[str, str]] = [
    {"lanes": "2"},
    # or placement:backward=left_of:1
    {"lanes": "3", "placement:forward": "left_of:1"},
    {"lanes": "3", "placement": "transition"},
    {"lanes": "4", "placement:backward": "middle_of:1"},
    {"lanes": "3"},
]


class Grid:
    """Creating map with elements ordered in grid."""

    def __init__(self, x_step: float = 0.0002, y_step: float = 0.0003):
        self.x_step: float = x_step
        self.y_step: float = y_step
        self.index: int = 0
        self.nodes: Dict[OSMNode, Tuple[int, int]] = {}
        self.max_j: float = 0
        self.max_i: float = 0
        self.way_id: int = 0
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
        self.max_j = max(self.max_j, j * self.x_step)
        self.max_i = max(self.max_i, i * self.y_step)
        return node

    def add_way(self, tags: Tags, nodes: list[OSMNode]) -> None:
        """Add OSM way to the grid."""
        osm_way: OSMWay = OSMWay(tags, self.way_id, nodes)
        self.osm_data.add_way(osm_way)
        self.way_id += 1

    def add_text(self, text: str, i: int, j: int) -> None:
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
            level="all", credit=None
        )
        flinger: Flinger = Flinger(
            self.get_boundary_box(), zoom, self.osm_data.equator_length
        )
        svg: Drawing = Drawing(output_path.name, flinger.size)
        constructor: Constructor = Constructor(
            self.osm_data, flinger, SCHEME, SHAPE_EXTRACTOR, configuration
        )
        constructor.construct()
        map_: Map = Map(flinger, svg, SCHEME, configuration)
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


def draw_overlapped_ways(types: list[dict[str, str]], path: Path) -> None:
    """
    Draw two sets of ways intersecting each other to show how they overlapping.
    """
    grid: Grid = Grid(0.00012, 0.00012)

    for index, tags in enumerate(types):
        node_1: OSMNode = grid.add_node({}, index + 1, 8)
        node_2: OSMNode = grid.add_node({}, index + 1, len(types) + 9)
        grid.add_way(tags, [node_1, node_2])
        grid.add_text(", ".join(f"{k}={tags[k]}" for k in tags), index + 1, 0)

    for index, tags in enumerate(types):
        node_1: OSMNode = grid.add_node({}, 0, index + 9)
        node_2: OSMNode = grid.add_node({}, len(types) + 1, index + 9)
        grid.add_way(tags, [node_1, node_2])

    grid.draw(path)


def draw_road_features(
    types: List[Dict[str, str]], features: List[Dict[str, str]], path: Path
) -> None:
    """Draw test image with different road features."""
    grid: Grid = Grid()

    for i, type_ in enumerate(types):
        previous: Optional[OSMNode] = None

        for j in range(len(features) + 1):
            node: OSMNode = grid.add_node({}, i, j)

            if previous:
                tags: Dict[str, str] = dict(type_)
                tags |= dict(features[j - 1])
                grid.add_way(tags, [previous, node])
            previous = node

    grid.draw(path)


if __name__ == "__main__":
    logging.basicConfig(format="%(levelname)s %(message)s", level=logging.INFO)

    out_path: Path = Path("out")

    road_tags: List[Dict[str, str]] = [
        {"highway": value} for value in ROAD_VALUES
    ]
    highway_tags: List[Dict[str, str]] = [
        {"highway": value} for value in HIGHWAY_VALUES
    ]
    aeroway_tags: List[Dict[str, str]] = [
        {"aeroway": value} for value in AEROWAY_VALUES
    ]
    railway_tags: list[dict[str, str]] = [
        {"railway": value} for value in RAILWAY_VALUES
    ]

    draw_road_features(
        highway_tags, ROAD_LANES_AND_FEATURES, out_path / "lanes.svg"
    )
    draw_road_features(
        highway_tags + railway_tags + aeroway_tags,
        ROAD_WIDTHS_AND_FEATURES,
        out_path / "width.svg",
    )
    draw_road_features(
        highway_tags,
        PLACEMENT_FEATURES_1 + [{"highway": "none"}] + PLACEMENT_FEATURES_2,
        out_path / "placement.svg",
    )
    draw_overlapped_ways(road_tags + railway_tags, out_path / "overlap.svg")
