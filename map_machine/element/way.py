"""Draw test nodes, ways, and relations."""

import logging
from pathlib import Path
from typing import Optional

from map_machine.element.grid import Grid
from map_machine.osm.osm_reader import OSMNode, OSMMember
from map_machine.osm.tags import (
    HIGHWAY_VALUES,
    AEROWAY_VALUES,
    RAILWAY_VALUES,
    ROAD_VALUES,
)

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


def draw_overlapped_ways(types: list[dict[str, str]], path: Path) -> None:
    """
    Draw two sets of ways intersecting each other.

    The goal is to show check priority.
    """
    grid: Grid = Grid()

    for index, tags in enumerate(types):
        node_1: OSMNode = grid.add_node({}, 8, index + 1)
        node_2: OSMNode = grid.add_node({}, len(types) + 9, index + 1)
        grid.add_way(tags, [node_1, node_2])
        grid.add_text(", ".join(f"{k}={tags[k]}" for k in tags), 0, index + 1)

    for index, tags in enumerate(types):
        node_1: OSMNode = grid.add_node({}, index + 9, 0)
        node_2: OSMNode = grid.add_node({}, index + 9, len(types) + 1)
        grid.add_way(tags, [node_1, node_2])

    grid.draw(path)


def draw_road_features(
    types: list[dict[str, str]], features: list[dict[str, str]], path: Path
) -> None:
    """Draw test image with different road features."""
    grid: Grid = Grid()

    for i, type_ in enumerate(types):
        previous: Optional[OSMNode] = None

        for j in range(len(features) + 1):
            node: OSMNode = grid.add_node({}, i, j)

            if previous:
                tags: dict[str, str] = dict(type_)
                tags |= dict(features[j - 1])
                grid.add_way(tags, [previous, node])
            previous = node

    grid.draw(path)


def draw_multipolygon(path: Path) -> None:
    """Draw simple multipolygon with one outer and one inner way."""
    grid: Grid = Grid()

    outer_node: OSMNode = grid.add_node({}, 0, 0)
    outer_nodes: list[OSMNode] = [
        outer_node,
        grid.add_node({}, 0, 3),
        grid.add_node({}, 3, 3),
        grid.add_node({}, 3, 0),
        outer_node,
    ]
    inner_node: OSMNode = grid.add_node({}, 1, 1)
    inner_nodes: list[OSMNode] = [
        inner_node,
        grid.add_node({}, 1, 2),
        grid.add_node({}, 2, 2),
        grid.add_node({}, 2, 1),
        inner_node,
    ]
    outer = grid.add_way({}, outer_nodes)
    inner = grid.add_way({}, inner_nodes)

    members: list[OSMMember] = [
        OSMMember("way", outer.id_, "outer"),
        OSMMember("way", inner.id_, "inner"),
    ]
    grid.add_relation({"natural": "water", "type": "multipolygon"}, members)

    grid.draw(path)


if __name__ == "__main__":
    logging.basicConfig(format="%(levelname)s %(message)s", level=logging.INFO)

    out_path: Path = Path("out")

    road_tags: list[dict[str, str]] = [
        {"highway": value} for value in ROAD_VALUES
    ]
    highway_tags: list[dict[str, str]] = [
        {"highway": value} for value in HIGHWAY_VALUES
    ]
    aeroway_tags: list[dict[str, str]] = [
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
    draw_multipolygon(out_path / "multipolygon.svg")
