"""
Röntgen entry point.

Author: Sergey Vartanov (me@enzet.ru).
"""
import argparse
import os
import sys
import svgwrite
import numpy as np

from roentgen import ui
from roentgen.constructor import Constructor
from roentgen.flinger import Flinger
from roentgen.grid import draw_all_icons
from roentgen.icon import IconExtractor
from roentgen.mapper import (
    Painter, check_level_number, check_level_overground,
    ICONS_FILE_NAME, AUTHOR_MODE, CREATION_TIME_MODE, TAGS_FILE_NAME
)
from roentgen.osm_getter import get_osm
from roentgen.osm_reader import Map, OSMReader, OverpassReader
from roentgen.point import Point
from roentgen.scheme import Scheme, LineStyle
from roentgen.util import MinMax


def main(argv) -> None:
    """
    Röntgen entry point.

    :param argv: command-line arguments
    """
    options: argparse.Namespace = ui.parse_options(argv)

    if not options:
        sys.exit(1)

    if options.input_file_name:
        input_file_name = options.input_file_name
    else:
        content = get_osm(options.boundary_box)
        if not content:
            ui.error("cannot download OSM data")
        input_file_name = [os.path.join("map", options.boundary_box + ".osm")]

    scheme: Scheme = Scheme(TAGS_FILE_NAME)

    if input_file_name[0].endswith(".json"):
        reader: OverpassReader = OverpassReader()
        reader.parse_json_file(input_file_name[0])
        map_ = reader.map_
        min1 = np.array((map_.boundary_box[0].min_, map_.boundary_box[1].min_))
        max1 = np.array((map_.boundary_box[0].max_, map_.boundary_box[1].max_))
    else:

        boundary_box = list(map(float, options.boundary_box.split(',')))

        full = False  # Full keys getting

        if options.mode in [AUTHOR_MODE, CREATION_TIME_MODE]:
            full = True

        osm_reader = OSMReader()

        for file_name in input_file_name:
            if not os.path.isfile(file_name):
                print("Fatal: no such file: " + file_name + ".")
                sys.exit(1)

            osm_reader.parse_osm_file(file_name, full=full)

        map_: Map = osm_reader.map_

        min1: np.array = np.array((boundary_box[1], boundary_box[0]))
        max1: np.array = np.array((boundary_box[3], boundary_box[2]))

    flinger: Flinger = Flinger(MinMax(min1, max1), options.scale)
    size: np.array = flinger.size

    svg: svgwrite.Drawing = (
        svgwrite.Drawing(options.output_file_name, size=size))

    icon_extractor: IconExtractor = IconExtractor(ICONS_FILE_NAME)

    def check_level(x) -> bool:
        """ Draw objects on all levels. """
        return True

    if options.level:
        if options.level == "overground":
            check_level = check_level_overground
        elif options.level == "underground":
            def check_level(x) -> bool:
                """ Draw underground objects. """
                return not check_level_overground(x)
        else:
            def check_level(x) -> bool:
                """ Draw objects on the specified level. """
                return not check_level_number(x, float(options.level))

    constructor: Constructor = Constructor(
        map_, flinger, scheme, icon_extractor, check_level, options.mode,
        options.seed)
    constructor.construct()

    painter: Painter = Painter(
        show_missing_tags=options.show_missing_tags, overlap=options.overlap,
        mode=options.mode, draw_captions=options.draw_captions,
        map_=map_, flinger=flinger, svg=svg, icon_extractor=icon_extractor,
        scheme=scheme)

    painter.draw(constructor)

    print("Writing output SVG...")
    svg.write(open(options.output_file_name, "w"))
    print("Done.")


def draw_element(target: str, tags_description: str):
    """
    Draw single node, line, or area.

    :param target: node, line, or area.
    :param tags_description: text description of tags, pair are separated by
        comma, key from value is separated by equals sign.
    """
    tags = dict([x.split("=") for x in tags_description.split(",")])
    scheme = Scheme("data/tags.yml")
    icon_extractor = IconExtractor("icons/icons.svg")
    icon_set, priority = scheme.get_icon(icon_extractor, tags)
    is_for_node: bool = target == "node"
    point = Point(
        icon_set, tags, np.array((32, 32)), None, is_for_node=is_for_node,
        draw_outline=is_for_node
    )
    print(point.is_for_node)
    svg = svgwrite.Drawing("test_icon.svg", (64, 64))
    for style in scheme.get_style(tags, 18):
        style: LineStyle
        path = svg.path(d="M 0,0 L 64,0 L 64,64 L 0,64 L 0,0 Z")
        path.update(style.style)
        svg.add(path)
    point.draw_main_shapes(svg)
    point.draw_extra_shapes(svg)
    point.draw_texts(svg, scheme, None, True)
    svg.write(open("test_icon.svg", "w+"))


def draw_grid():
    """
    Draw all possible icon shapes combinations as grid.
    """
    os.makedirs("icon_set", exist_ok=True)
    draw_all_icons("icon_grid.svg", "icon_set")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] in ["node", "way", "area"]:
        draw_element(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 2 and sys.argv[1] == "grid":
        draw_grid()
    else:
        main(sys.argv)
