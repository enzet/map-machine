"""
Actions to perform before commit: generate PNG images for documentation.
"""
import logging
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import svgwrite

from map_machine.geometry.boundary_box import BoundaryBox
from map_machine.constructor import Constructor
from map_machine.geometry.flinger import Flinger
from map_machine.pictogram.icon import ShapeExtractor
from map_machine.mapper import Map
from map_machine.map_configuration import (
    BuildingMode,
    DrawingMode,
    LabelMode,
    MapConfiguration,
)
from map_machine.osm.osm_getter import get_osm
from map_machine.osm.osm_reader import OSMData
from map_machine.scheme import Scheme

doc_path: Path = Path("doc")

cache: Path = Path("cache")
cache.mkdir(exist_ok=True)

SCHEME = Scheme.from_file(Path("map_machine/scheme/default.yml"))
EXTRACTOR: ShapeExtractor = ShapeExtractor(
    Path("map_machine/icons/icons.svg"),
    Path("map_machine/icons/config.json"),
)


def draw(
    input_file_name: Path,
    output_file_name: Path,
    boundary_box: BoundaryBox,
    configuration: MapConfiguration = MapConfiguration(),
) -> None:
    """Draw file."""
    osm_data: OSMData = OSMData()
    osm_data.parse_osm_file(input_file_name)
    flinger = Flinger(
        boundary_box, configuration.zoom_level, osm_data.equator_length
    )
    constructor: Constructor = Constructor(
        osm_data, flinger, SCHEME, EXTRACTOR, configuration
    )
    constructor.construct()

    svg: svgwrite.Drawing = svgwrite.Drawing(
        str(output_file_name), size=flinger.size
    )
    map_: Map = Map(flinger, svg, SCHEME, configuration)
    map_.draw(constructor)

    svg.write(output_file_name.open("w"))


def draw_around_point(
    point: np.ndarray,
    name: str,
    configuration: MapConfiguration = MapConfiguration(),
    size: np.ndarray = np.array((600, 400)),
    get: Optional[BoundaryBox] = None,
) -> None:
    """Draw around point."""
    input_path: Path = doc_path / f"{name}.svg"

    boundary_box: BoundaryBox = BoundaryBox.from_coordinates(
        point, configuration.zoom_level, size[0], size[1]
    )
    get_boundary_box = get if get else boundary_box

    get_osm(get_boundary_box, cache / f"{get_boundary_box.get_format()}.osm")
    draw(
        cache / f"{get_boundary_box.get_format()}.osm",
        input_path,
        boundary_box,
        configuration,
    )


def main(id_: str) -> None:
    """Entry point."""
    if id_ is None or id_ in ["draw", "fitness"]:
        draw_around_point(
            np.array((55.75277, 37.40856)),
            "fitness",
            MapConfiguration(zoom_level=20.2),
            np.array((300, 200)),
        )

    if id_ is None or id_ in ["draw", "power"]:
        draw_around_point(
            np.array((52.5622, 12.94)),
            "power",
            configuration=MapConfiguration(zoom_level=15),
        )

    if id_ is None or id_ in ["draw", "playground"]:
        draw_around_point(
            np.array((52.47388, 13.43826)),
            "playground",
            configuration=MapConfiguration(zoom_level=19),
        )

    # Playground: (59.91991/10.85535), (59.83627/10.83017), Oslo
    # (52.47604/13.43701), (52.47388/13.43826)*, Berlin

    if id_ is None or id_ in ["draw", "surveillance"]:
        draw_around_point(
            np.array((52.50892, 13.3244)),
            "surveillance",
            MapConfiguration(
                zoom_level=18.5,
                ignore_level_matching=True,
            ),
        )

    if id_ is None or id_ in ["draw", "viewpoints"]:
        draw_around_point(
            np.array((52.421, 13.101)),
            "viewpoints",
            MapConfiguration(
                label_mode=LabelMode.NO,
                zoom_level=15.7,
                ignore_level_matching=True,
            ),
        )

    if id_ is None or id_ in ["draw", "buildings"]:
        draw_around_point(
            np.array((-26.19049, 28.05605)),
            "buildings",
            MapConfiguration(building_mode=BuildingMode.ISOMETRIC),
        )

    if id_ is None or id_ in ["draw", "trees"]:
        draw_around_point(
            np.array((55.751, 37.628)),
            "trees",
            MapConfiguration(
                label_mode=LabelMode(LabelMode.ALL), zoom_level=18.1
            ),
            get=BoundaryBox(37.624, 55.749, 37.633, 55.753),
        )

    # if id_ is None or id_ == "golf":
    #     tiles = Tiles(np.array((52.5859, 13.4644)), 17, 2, 3)
    #     tiles.draw()

    if id_ is None or id_ in ["draw", "time"]:
        draw_around_point(
            np.array((55.7655, 37.6055)),
            "time",
            MapConfiguration(
                DrawingMode.TIME,
                zoom_level=16.5,
                ignore_level_matching=True,
            ),
        )

    if id_ is None or id_ in ["draw", "author"]:
        draw_around_point(
            np.array((55.7655, 37.6055)),
            "author",
            MapConfiguration(
                DrawingMode.AUTHOR,
                seed="a",
                zoom_level=16.5,
                ignore_level_matching=True,
            ),
        )

    if id_ is None or id_ in ["draw", "colors"]:
        draw_around_point(
            np.array((48.87422, 2.377)),
            "colors",
            configuration=MapConfiguration(
                zoom_level=17.6,
                building_mode=BuildingMode.ISOMETRIC,
                ignore_level_matching=True,
            ),
        )

    if id_ is None or id_ in ["draw", "lanes"]:
        draw_around_point(np.array((47.61224, -122.33866)), "lanes")


if __name__ == "__main__":
    logging.basicConfig(format="%(levelname)s %(message)s", level=logging.DEBUG)
    main(None if len(sys.argv) < 2 else sys.argv[1])
