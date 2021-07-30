"""
Röntgen entry point.

Author: Sergey Vartanov (me@enzet.ru).
"""
import argparse
import sys
from pathlib import Path
from typing import List, Set

import logging
import numpy as np
import svgwrite

from roentgen import server, tile
from roentgen.constructor import Constructor
from roentgen.flinger import Flinger
from roentgen.grid import draw_icons
from roentgen.icon import ShapeExtractor
from roentgen.mapper import (
    AUTHOR_MODE,
    CREATION_TIME_MODE,
    ICONS_FILE_NAME,
    Painter,
    TAGS_FILE_NAME,
    check_level_number,
    check_level_overground,
)
from roentgen.osm_getter import get_osm
from roentgen.osm_reader import Map, OSMReader, OverpassReader
from roentgen.point import Point
from roentgen.scheme import LineStyle, Scheme
from roentgen.ui import error, parse_options
from roentgen.util import MinMax


def main(options) -> None:
    """
    Röntgen entry point.

    :param argv: command-line arguments
    """
    if options.boundary_box:
        options.boundary_box = options.boundary_box.replace(" ", "")

    cache_path: Path = Path(options.cache)
    cache_path.mkdir(parents=True, exist_ok=True)

    input_file_names: List[Path]

    if options.input_file_name:
        input_file_names = list(map(Path, options.input_file_name))
    else:
        content = get_osm(options.boundary_box, cache_path)
        if not content:
            error("cannot download OSM data")
            sys.exit(1)
        input_file_names = [cache_path / f"{options.boundary_box}.osm"]

    scheme: Scheme = Scheme(Path(TAGS_FILE_NAME))
    min_: np.array
    max_: np.array
    map_: Map

    if input_file_names[0].name.endswith(".json"):
        reader: OverpassReader = OverpassReader()
        reader.parse_json_file(input_file_names[0])

        map_ = reader.map_
        view_box = MinMax(
            np.array((map_.boundary_box[0].min_, map_.boundary_box[1].min_)),
            np.array((map_.boundary_box[0].max_, map_.boundary_box[1].max_)),
        )
    else:
        is_full: bool = options.mode in [AUTHOR_MODE, CREATION_TIME_MODE]
        osm_reader = OSMReader(is_full=is_full)

        for file_name in input_file_names:
            if not file_name.is_file():
                print(f"Fatal: no such file: {file_name}.")
                sys.exit(1)

            osm_reader.parse_osm_file(file_name)

        map_ = osm_reader.map_

        if options.boundary_box:
            boundary_box: List[float] = list(
                map(float, options.boundary_box.split(","))
            )
            view_box = MinMax(
                np.array((boundary_box[1], boundary_box[0])),
                np.array((boundary_box[3], boundary_box[2])),
            )
        else:
            view_box = map_.view_box

    flinger: Flinger = Flinger(view_box, options.scale)
    size: np.array = flinger.size

    Path("out").mkdir(parents=True, exist_ok=True)

    svg: svgwrite.Drawing = svgwrite.Drawing(
        options.output_file_name, size=size
    )
    icon_extractor: ShapeExtractor = ShapeExtractor(
        Path(ICONS_FILE_NAME), Path("icons/config.json")
    )

    if options.level:
        if options.level == "overground":
            check_level = check_level_overground
        elif options.level == "underground":

            def check_level(x) -> bool:
                """Draw underground objects."""
                return not check_level_overground(x)

        else:

            def check_level(x) -> bool:
                """Draw objects on the specified level."""
                return not check_level_number(x, float(options.level))

    else:

        def check_level(_) -> bool:
            """Draw objects on any level."""
            return True

    constructor: Constructor = Constructor(
        map_,
        flinger,
        scheme,
        icon_extractor,
        check_level,
        options.mode,
        options.seed,
    )
    constructor.construct()

    painter: Painter = Painter(
        overlap=options.overlap,
        mode=options.mode,
        label_mode=options.label_mode,
        map_=map_,
        flinger=flinger,
        svg=svg,
        icon_extractor=icon_extractor,
        scheme=scheme,
    )

    painter.draw(constructor)

    print(f"Writing output SVG to {options.output_file_name}...")
    with open(options.output_file_name, "w") as output_file:
        svg.write(output_file)


def draw_element(options):
    """
    Draw single node, line, or area.

    :param target: node, line, or area.
    :param tags_description: text description of tags, pair are separated by
        comma, key from value is separated by equals sign.
    """
    if options.node:
        target = "node"
        tags_description = options.node
    else:
        # Not implemented yet.
        sys.exit(1)

    tags = dict([x.split("=") for x in tags_description.split(",")])
    scheme: Scheme = Scheme(Path("scheme/default.yml"))
    extractor: ShapeExtractor = ShapeExtractor(
        Path("icons/icons.svg"), Path("icons/config.json")
    )
    processed: Set[str] = set()
    icon, priority = scheme.get_icon(extractor, tags, processed)
    is_for_node: bool = target == "node"
    labels = scheme.construct_text(tags, "all", processed)
    point = Point(
        icon,
        labels,
        tags,
        processed,
        np.array((32, 32)),
        None,
        is_for_node=is_for_node,
        draw_outline=is_for_node,
    )
    border: np.array = np.array((16, 16))
    size: np.array = point.get_size() + border
    point.point = np.array((size[0] / 2, 16 / 2 + border[1] / 2))

    Path("out").mkdir(parents=True, exist_ok=True)
    svg = svgwrite.Drawing("out/element.svg", size.astype(float))
    for style in scheme.get_style(tags, 18):
        style: LineStyle
        path = svg.path(d="M 0,0 L 64,0 L 64,64 L 0,64 L 0,0 Z")
        path.update(style.style)
        svg.add(path)
    point.draw_main_shapes(svg)
    point.draw_extra_shapes(svg)
    point.draw_texts(svg)
    svg.write(open("out/element.svg", "w+"))


def init_scheme() -> Scheme:
    return Scheme(Path("scheme/default.yml"))


if __name__ == "__main__":

    logging.basicConfig(format="%(levelname)s %(message)s", level=logging.INFO)

    options: argparse.Namespace = parse_options(sys.argv)

    if options.command == "render":
        main(options)
    elif options.command == "tile":
        tile.ui(options)
    elif options.command == "icons":
        draw_icons()
    elif options.command == "mapcss":
        from roentgen.mapcss import write_mapcss

        write_mapcss()
    elif options.command == "element":
        draw_element(options)
    elif options.command == "server":
        server.ui(sys.argv[2:])
    elif options.command == "taginfo":
        from roentgen.taginfo import write_taginfo_project_file

        write_taginfo_project_file(init_scheme())
