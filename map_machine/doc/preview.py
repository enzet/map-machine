"""Actions to perform before commit: generate PNG images for documentation."""

import logging
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import svgwrite

from map_machine.constructor import Constructor
from map_machine.geometry.boundary_box import BoundaryBox
from map_machine.geometry.flinger import MercatorFlinger
from map_machine.map_configuration import (
    BuildingMode,
    DrawingMode,
    LabelMode,
    MapConfiguration,
)
from map_machine.mapper import Map
from map_machine.osm.osm_getter import get_osm
from map_machine.osm.osm_reader import OSMData
from map_machine.pictogram.icon import ShapeExtractor
from map_machine.scheme import Scheme
from map_machine.workspace import workspace

doc_path: Path = Path("doc")

cache: Path = Path("cache")
cache.mkdir(exist_ok=True)

SCHEME: Scheme = Scheme.from_file(workspace.DEFAULT_SCHEME_PATH)
EXTRACTOR: ShapeExtractor = ShapeExtractor(
    workspace.ICONS_PATH, workspace.ICONS_CONFIG_PATH
)


def draw(
    input_file_name: Path,
    output_file_name: Path,
    boundary_box: BoundaryBox,
    configuration: Optional[MapConfiguration] = None,
) -> None:
    """Draw file."""
    if configuration is None:
        configuration = MapConfiguration(SCHEME)

    osm_data: OSMData = OSMData()
    osm_data.parse_osm_file(input_file_name)
    flinger: MercatorFlinger = MercatorFlinger(
        boundary_box, configuration.zoom_level, osm_data.equator_length
    )
    constructor: Constructor = Constructor(
        osm_data, flinger, EXTRACTOR, configuration
    )
    constructor.construct()

    svg: svgwrite.Drawing = svgwrite.Drawing(
        str(output_file_name), size=flinger.size
    )
    map_: Map = Map(flinger, svg, configuration)
    map_.draw(constructor)

    svg.write(output_file_name.open("w"))


def draw_around_point(
    point: np.ndarray,
    name: str,
    configuration: Optional[MapConfiguration] = None,
    size: np.ndarray = np.array((600, 400)),
    get: Optional[BoundaryBox] = None,
) -> None:
    """Draw around point."""
    if configuration is None:
        configuration = MapConfiguration(SCHEME)

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
    # if id_ is None or id_ == "fitness":
    #     draw_around_point(
    #         np.array((55.75277, 37.40856)),
    #         "fitness",
    #         MapConfiguration(SCHEME, zoom_level=20.2),
    #         np.array((300, 200)),
    #     )

    if id_ is None or id_ == "power":
        draw_around_point(
            np.array((52.5622, 12.94)),
            "power",
            configuration=MapConfiguration(SCHEME, zoom_level=15),
        )

    # if id_ is None or id_ == "playground":
    #     draw_around_point(
    #         np.array((52.47388, 13.43826)),
    #         "playground",
    #         configuration=MapConfiguration(SCHEME, zoom_level=19),
    #     )

    # Playground: (59.91991/10.85535), (59.83627/10.83017), Oslo
    # (52.47604/13.43701), (52.47388/13.43826)*, Berlin

    if id_ is None or id_ == "surveillance":
        draw_around_point(
            np.array((52.50892, 13.3244)),
            "surveillance",
            MapConfiguration(
                SCHEME,
                zoom_level=18.5,
                ignore_level_matching=True,
            ),
        )

    if id_ is None or id_ == "viewpoints":
        draw_around_point(
            np.array((52.421, 13.101)),
            "viewpoints",
            MapConfiguration(
                SCHEME,
                label_mode=LabelMode.NO,
                zoom_level=15.7,
                ignore_level_matching=True,
            ),
        )

    if id_ is None or id_ == "buildings":
        draw_around_point(
            np.array((-26.19049, 28.05605)),
            "buildings",
            MapConfiguration(SCHEME, building_mode=BuildingMode.ISOMETRIC),
        )

    if id_ is None or id_ == "trees":
        draw_around_point(
            np.array((55.751, 37.628)),
            "trees",
            MapConfiguration(
                SCHEME, label_mode=LabelMode(LabelMode.ALL), zoom_level=18.1
            ),
            get=BoundaryBox(37.624, 55.749, 37.633, 55.753),
        )

    # if id_ is None or id_ == "golf":
    #     tiles = Tiles(np.array((52.5859, 13.4644)), 17, 2, 3)
    #     tiles.draw()

    if id_ is None or id_ == "time":
        draw_around_point(
            np.array((55.7655, 37.6055)),
            "time",
            MapConfiguration(
                SCHEME,
                DrawingMode.TIME,
                zoom_level=16.5,
                ignore_level_matching=True,
            ),
        )

    if id_ is None or id_ == "author":
        draw_around_point(
            np.array((55.7655, 37.6055)),
            "author",
            MapConfiguration(
                SCHEME,
                DrawingMode.AUTHOR,
                seed="a",
                zoom_level=16.5,
                ignore_level_matching=True,
            ),
        )

    if id_ is None or id_ == "colors":
        draw_around_point(
            np.array((48.87422, 2.377)),
            "colors",
            configuration=MapConfiguration(
                SCHEME,
                zoom_level=17.6,
                building_mode=BuildingMode.ISOMETRIC,
                ignore_level_matching=True,
            ),
        )

    if id_ is None or id_ == "lanes":
        draw_around_point(np.array((47.61224, -122.33866)), "lanes")

    if id_ is None or id_ == "indoor":
        draw_around_point(
            np.array((4.5978, -74.07507)),
            "indoor",
            configuration=MapConfiguration(SCHEME, zoom_level=19.5, level="0"),
        )


if __name__ == "__main__":
    logging.basicConfig(format="%(levelname)s %(message)s", level=logging.DEBUG)
    main(None if len(sys.argv) < 2 else sys.argv[1])
