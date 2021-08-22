"""
Röntgen entry point.

Author: Sergey Vartanov (me@enzet.ru).
"""
import argparse
import logging
import sys
from pathlib import Path
from typing import List, Set

import numpy as np
import svgwrite

from roentgen.constructor import Constructor
from roentgen.flinger import Flinger
from roentgen.grid import draw_icons
from roentgen.icon import ShapeExtractor
from roentgen.mapper import (
    AUTHOR_MODE,
    TIME_MODE,
    Map,
    check_level_number,
    check_level_overground,
)
from roentgen.osm_getter import NetworkError, get_osm
from roentgen.osm_reader import OSMData, OSMReader, OverpassReader
from roentgen.point import Point
from roentgen.scheme import LineStyle, Scheme
from roentgen.ui import BoundaryBox, parse_options
from roentgen.util import MinMax
from roentgen.workspace import Workspace


def main(options) -> None:
    """
    Röntgen entry point.

    :param options: command-line arguments
    """
    if not options.boundary_box and not options.input_file_name:
        logging.fatal("Specify either --boundary-box, or --input.")
        exit(1)

    if options.boundary_box:
        boundary_box: BoundaryBox = BoundaryBox.from_text(options.boundary_box)

    cache_path: Path = Path(options.cache)
    cache_path.mkdir(parents=True, exist_ok=True)

    input_file_names: List[Path]

    if options.input_file_name:
        input_file_names = list(map(Path, options.input_file_name))
    else:
        try:
            cache_file_path: Path = (
                cache_path / f"{boundary_box.get_format()}.osm"
            )
            get_osm(boundary_box, cache_file_path)
        except NetworkError as e:
            logging.fatal(e.message)
            sys.exit(1)
        input_file_names = [cache_file_path]

    scheme: Scheme = Scheme(workspace.DEFAULT_SCHEME_PATH)
    min_: np.array
    max_: np.array
    osm_data: OSMData

    if input_file_names[0].name.endswith(".json"):
        reader: OverpassReader = OverpassReader()
        reader.parse_json_file(input_file_names[0])

        osm_data = reader.osm_data
        view_box = MinMax(
            np.array(
                (osm_data.boundary_box[0].min_, osm_data.boundary_box[1].min_)
            ),
            np.array(
                (osm_data.boundary_box[0].max_, osm_data.boundary_box[1].max_)
            ),
        )
    else:
        is_full: bool = options.mode in [AUTHOR_MODE, TIME_MODE]
        osm_reader = OSMReader(is_full=is_full)

        for file_name in input_file_names:
            if not file_name.is_file():
                print(f"Fatal: no such file: {file_name}.")
                sys.exit(1)

            osm_reader.parse_osm_file(file_name)

        osm_data = osm_reader.osm_data

        if options.boundary_box:
            view_box = MinMax(
                np.array((boundary_box.bottom, boundary_box.left)),
                np.array((boundary_box.top, boundary_box.right)),
            )
        else:
            view_box = osm_data.view_box

    flinger: Flinger = Flinger(view_box, options.scale)
    size: np.array = flinger.size

    svg: svgwrite.Drawing = svgwrite.Drawing(
        options.output_file_name, size=size
    )
    icon_extractor: ShapeExtractor = ShapeExtractor(
        workspace.ICONS_PATH, workspace.ICONS_CONFIG_PATH
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
        osm_data,
        flinger,
        scheme,
        icon_extractor,
        check_level,
        options.mode,
        options.seed,
    )
    constructor.construct()

    painter: Map = Map(
        overlap=options.overlap,
        mode=options.mode,
        label_mode=options.label_mode,
        flinger=flinger,
        svg=svg,
        scheme=scheme,
    )
    painter.draw(constructor)

    print(f"Writing output SVG to {options.output_file_name}...")
    with open(options.output_file_name, "w") as output_file:
        svg.write(output_file)


def draw_element(options) -> None:
    """Draw single node, line, or area."""
    if options.node:
        target: str = "node"
        tags_description = options.node
    else:
        # Not implemented yet.
        sys.exit(1)

    tags: dict[str, str] = dict(
        [x.split("=") for x in tags_description.split(",")]
    )
    scheme: Scheme = Scheme(workspace.DEFAULT_SCHEME_PATH)
    extractor: ShapeExtractor = ShapeExtractor(
        workspace.ICONS_PATH, workspace.ICONS_CONFIG_PATH
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

    output_file_path: Path = workspace.output_path / "element.svg"
    svg = svgwrite.Drawing(str(output_file_path), size.astype(float))
    for style in scheme.get_style(tags):
        style: LineStyle
        path = svg.path(d="M 0,0 L 64,0 L 64,64 L 0,64 L 0,0 Z")
        path.update(style.style)
        svg.add(path)
    point.draw_main_shapes(svg)
    point.draw_extra_shapes(svg)
    point.draw_texts(svg)
    with output_file_path.open("w+") as output_file:
        svg.write(output_file)
    logging.info(f"Element is written to {output_file_path}.")


def init_scheme() -> Scheme:
    """Initialize default scheme."""
    return Scheme(workspace.DEFAULT_SCHEME_PATH)


if __name__ == "__main__":

    logging.basicConfig(format="%(levelname)s %(message)s", level=logging.INFO)
    workspace: Workspace = Workspace(Path("out"))

    arguments: argparse.Namespace = parse_options(sys.argv)

    if arguments.command == "render":
        main(arguments)

    elif arguments.command == "tile":
        from roentgen import tile

        tile.ui(arguments)

    elif arguments.command == "icons":
        draw_icons()

    elif arguments.command == "mapcss":
        from roentgen import mapcss

        mapcss.ui(arguments)

    elif arguments.command == "element":
        draw_element(arguments)

    elif arguments.command == "server":
        from roentgen import server

        server.ui(arguments)

    elif arguments.command == "taginfo":
        from roentgen.taginfo import write_taginfo_project_file

        write_taginfo_project_file(init_scheme())
