"""
Special icon collections for documentation.
"""
from dataclasses import dataclass, field
from typing import Optional

from map_machine.osm.osm_reader import Tags


@dataclass
class Collection:
    """Icon collection."""

    page_name: str
    tags: Tags
    row_key: str = None
    row_values: list[str] = field(default_factory=list)
    column_key: Optional[str] = None
    column_values: list[str] = field(default_factory=list)


tower_type_values: list[str] = [
    "communication",
    "lighting",
    "monitoring",
    "siren",
]

collections = [
    Collection(
        "Tag:man_made=mast",
        {"man_made": "mast"},
        "tower:construction",
        ["freestanding", "lattice", "guyed_tube", "guyed_lattice"],
        "tower:type",
        [""] + tower_type_values,
    ),
    Collection(
        "Tag:man_made=mast",
        {"man_made": "mast"},
        "tower:construction",
        ["freestanding", "lattice", "guyed_tube", "guyed_lattice"],
        "tower:type",
        [""] + tower_type_values,
    ),
    Collection(
        "Tag:tower:construction=guyed_tube",
        {"man_made": "mast", "tower:construction": "guyed_tube"},
        "tower:type",
        [""] + tower_type_values,
    ),
    Collection(
        "Tag:tower:construction=guyed_lattice",
        {"man_made": "mast", "tower:construction": "guyed_lattice"},
        "tower:type",
        [""] + tower_type_values,
    ),
    Collection(
        "Key:communication:mobile_phone",
        {"communication:mobile_phone": "yes"},
    ),
    Collection(
        "Key:traffic_calming",
        {},
        "traffic_calming",
        [
            "bump",
            "mini_bumps",
            "hump",
            "table",
            "cushion",
            "rumble_strip",
            "dip",
            "double_dip",
            # "dynamic_bump", "chicane",
            # "choker", "island", "chocked_island", "chocked_table",
        ],
    ),
    Collection(
        "Key:crane:type",
        {"man_made": "crane"},
        "crane:type",
        [
            "gantry_crane",
            "floor-mounted_crane",
            "portal_crane",
            "travel_lift",
            "tower_crane",
        ],
    ),
    Collection(
        "Tag:tower:type=diving",
        {"man_made": "tower", "tower:type": "diving"},
    ),
]
