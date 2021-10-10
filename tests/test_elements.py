"""
Draw test nodes, ways, and relations.
"""
from pathlib import Path
from typing import Optional

import numpy as np
from svgwrite import Drawing

from map_machine.boundary_box import BoundaryBox
from map_machine.constructor import Constructor
from map_machine.flinger import Flinger
from map_machine.icon import ShapeExtractor
from map_machine.map_configuration import MapConfiguration
from map_machine.mapper import Map
from map_machine.osm_reader import OSMData, OSMNode, OSMWay
from map_machine.scheme import Scheme
from map_machine.workspace import Workspace

workspace: Workspace = Workspace(Path("temp"))

SCHEME: Scheme = Scheme(workspace.DEFAULT_SCHEME_PATH)
SHAPE_EXTRACTOR: ShapeExtractor = ShapeExtractor(
    workspace.ICONS_PATH, workspace.ICONS_CONFIG_PATH
)


ROAD_TYPES: list[dict[str, str]] = [
    {"highway": "motorway"},
    {"highway": "trunk"},
    {"highway": "primary"},
    {"highway": "secondary"},
    {"highway": "tertiary"},
    {"highway": "unclassified"},
    {"highway": "residential"},
    {"highway": "service"},
    {"highway": "service_minor"},
    {"highway": "road"},
    {"highway": "pedestrian"},
    {"highway": "living_street"},
    {"highway": "bridleway"},
    {"highway": "cycleway"},
    {"highway": "footway"},
    {"highway": "steps"},
    {"highway": "path"},
    {"highway": "track"},
    {"highway": "raceway"},
    {"highway": "runway"},
    {"highway": "taxiway"},
    {"railway": "rail"},
    {"railway": "light_rail"},
    {"railway": "monorail"},
    {"railway": "funicular"},
    {"railway": "narrow_gauge"},
    {"railway": "subway"},
    {"railway": "subway", "color": "red"},
    {"railway": "subway", "color": "blue"},
]


ROAD_FEATURES: list[dict[str, str]] = [
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


class Grid:
    """
    Creating map with elements ordered in grid.
    """

    def __init__(self) -> None:
        self.x_step: float = 0.0003
        self.y_step: float = 0.0003
        self.x_start: float = 0.0028
        self.index: int = 0
        self.nodes: dict[OSMNode, tuple[int, int]] = {}
        self.max_j: float = 0
        self.max_i: float = 0

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


def lanes() -> None:
    """Draw test image with different road features."""
    osm_data: OSMData = OSMData()

    grid: Grid = Grid()

    for i in range(len(ROAD_TYPES)):
        previous: Optional[OSMNode] = None

        for j in range(len(ROAD_FEATURES) + 1):
            node: OSMNode = grid.add_node({}, i, j)

            if previous:
                tags: dict[str, str] = dict(ROAD_FEATURES[j - 1])
                tags |= ROAD_TYPES[i]
                way: OSMWay = OSMWay(
                    tags, i * (len(ROAD_FEATURES) + 1) + j, [previous, node]
                )
                osm_data.add_way(way)
            previous = node

    draw(osm_data, Path("out") / "lanes.svg", grid.get_boundary_box())


def draw(
    osm_data: OSMData, output_path: Path, boundary_box: BoundaryBox
) -> None:
    """Draw map."""
    configuration: MapConfiguration = MapConfiguration(level="all")

    flinger: Flinger = Flinger(
        boundary_box,
        18,
        osm_data.equator_length,
    )
    svg: Drawing = Drawing(output_path.name, flinger.size)
    constructor: Constructor = Constructor(
        osm_data, flinger, SCHEME, SHAPE_EXTRACTOR, configuration
    )
    constructor.construct()
    map_: Map = Map(flinger, svg, SCHEME, configuration)
    map_.draw(constructor)

    with output_path.open("w") as output_file:
        svg.write(output_file)


if __name__ == "__main__":
    lanes()
