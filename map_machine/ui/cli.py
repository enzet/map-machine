"""Command-line user interface."""

import argparse

from map_machine import __version__
from map_machine.map_configuration import BuildingMode, DrawingMode, LabelMode
from map_machine.osm.osm_reader import STAGES_OF_DECAY

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

COMMAND_LINES: dict[str, list[str]] = {
    "render": ["render", "-b", "10.000,20.000,10.001,20.001"],
    "render_with_tooltips": [
        "render",
        "-b",
        "10.000,20.000,10.001,20.001",
        "--tooltips",
    ],
    "icons": ["icons"],
    "mapcss": ["mapcss"],
    "draw": ["draw", "node", "amenity=bench,material=wood"],
    "tile": ["tile", "--coordinates", "50.000,40.000"],
}
COMMANDS: list[str] = [
    "render",
    "server",
    "tile",
    "element",
    "mapcss",
    "icons",
    "taginfo",
]


def parse_arguments(args: list[str]) -> argparse.Namespace:
    """Parse Map Machine command-line arguments."""

    # Preparse arguments adding space before coordinates and boundary box if the
    # first value is negative.  In that case `argparse` interprets in as an
    # option name.
    for argument in "-c", "--coordinates", "-b", "--boundary-box":
        if argument in args:
            index: int = args.index(argument) + 1
            if args[index].startswith("-"):
                args[index] = " " + args[index]
            break

    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Map Machine. OpenStreetMap renderer with custom icon set"
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="Map Machine " + __version__,
    )
    subparser = parser.add_subparsers(dest="command")

    render_parser = subparser.add_parser(
        "render",
        description="Render SVG map.  Use --boundary-box to specify geo "
        "boundaries, --input to specify OSM XML or JSON input file, or "
        "--coordinates and --size to specify central point and resulting image "
        "size.",
        help="draw SVG map",
    )
    add_render_arguments(render_parser)
    add_map_arguments(render_parser)

    tile_parser = subparser.add_parser(
        "tile",
        description="Generate SVG and PNG 256 × 256 px tiles for slippy maps.  "
        "You can use server command to run server in order to display "
        "generated tiles as a map (e.g. with Leaflet).",
        help="generate SVG and PNG tiles for slippy maps",
    )
    add_tile_arguments(tile_parser)
    add_map_arguments(tile_parser)

    add_server_arguments(
        subparser.add_parser(
            "server",
            description="Run in order to display generated tiles as a map "
            "(e.g. with Leaflet).",
            help="run tile server",
        )
    )
    add_draw_arguments(
        subparser.add_parser(
            "draw",
            description="Draw map element separately.",
            help="draw OSM element: node, way, relation",
        )
    )
    add_mapcss_arguments(
        subparser.add_parser(
            "mapcss",
            description="Write directory with MapCSS file and generated "
            "Röntgen icons.",
            help="write MapCSS file",
        )
    )

    subparser.add_parser(
        "icons",
        description="Generate Röntgen icons as a grid and as separate SVG "
        "icons",
        help="draw Röntgen icons",
    )
    subparser.add_parser(
        "taginfo",
        description="Generate JSON file for Taginfo project.",
        help="write Taginfo JSON file",
    )

    arguments: argparse.Namespace = parser.parse_args(args[1:])

    return arguments


def add_map_arguments(parser: argparse.ArgumentParser) -> None:
    """Add map-specific arguments."""
    parser.add_argument(
        "--scheme",
        metavar="<id> or <path>",
        default="default",
        help="scheme identifier (look for `<id>.yml` file) or path to a YAML "
        "scheme file",
    )
    parser.add_argument(
        "--buildings",
        metavar="<mode>",
        default="flat",
        choices=(mode.value for mode in BuildingMode),
        help="building drawing mode: "
        + ", ".join(mode.value for mode in BuildingMode),
    )
    parser.add_argument(
        "--mode",
        default="normal",
        metavar="<string>",
        choices=(mode.value for mode in DrawingMode),
        help="map drawing mode: "
        + ", ".join(mode.value for mode in DrawingMode),
    )
    parser.add_argument(
        "--overlap",
        dest="overlap",
        default=12,
        type=int,
        help="how many pixels should be left around icons and text",
        metavar="<integer>",
    )
    parser.add_argument(
        "--labels",
        dest="label_mode",
        default="main",
        metavar="<string>",
        choices=(mode.value for mode in LabelMode),
        help="label drawing mode: "
        + ", ".join(mode.value for mode in LabelMode),
    )
    parser.add_argument(
        "--level",
        default="overground",
        help="display only this floor level",
    )
    parser.add_argument(
        "--seed",
        default="",
        help="seed for random",
        metavar="<string>",
    )
    parser.add_argument(
        "--tooltips",
        help="add tooltips with tags for icons in SVG files",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    parser.add_argument(
        "--country",
        help="two-letter code (ISO 3166-1 alpha-2) of country, that should be "
        "used for location restrictions",
        default="world",
    )
    parser.add_argument(
        "--ignore-level-matching",
        help="draw all map features ignoring the current level",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    parser.add_argument(
        "--roofs",
        help="draw building roofs",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--building-colors",
        help="paint walls (if isometric mode is enabled) and roofs with "
        "specified colors",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    parser.add_argument(
        "--show-overlapped",
        help="show hidden nodes with a dot",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    parser.add_argument(
        "--hide-credit",
        help="hide credit",
        action=argparse.BooleanOptionalAction,
        default=False,
    )


def add_tile_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for tile command."""
    parser.add_argument(
        "-c",
        "--coordinates",
        metavar="<latitude>,<longitude>",
        help="coordinates of any location inside the tile",
    )
    parser.add_argument(
        "-t",
        "--tile",
        metavar="<zoom level>/<x>/<y>",
        help="tile specification",
    )
    parser.add_argument(
        "--cache",
        help="path for temporary OSM files",
        default="cache",
        metavar="<path>",
    )
    parser.add_argument(
        "-b",
        "--boundary-box",
        help="construct the minimum amount of tiles that cover the requested "
        "boundary box",
        metavar="<lon1>,<lat1>,<lon2>,<lat2>",
    )
    parser.add_argument(
        "-z",
        "--zoom",
        type=str,
        metavar="<range>",
        help="OSM zoom levels; can be list of numbers or ranges, e.g. `16-18`, "
        "`16,17,18`, or `16,18-20`",
        default="18",
    )
    parser.add_argument(
        "-i",
        "--input",
        dest="input_file_name",
        metavar="<path>",
        help="input OSM XML file name (if not specified, the file will be "
        "downloaded using the OpenStreetMap API)",
    )


def add_server_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for server command."""
    parser.add_argument(
        "--cache",
        help="path for temporary OSM files",
        default="cache",
        metavar="<path>",
    )
    parser.add_argument(
        "--port",
        help="port number",
        default=8080,
        type=int,
        metavar="<integer>",
    )


def add_draw_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for element command."""
    parser.add_argument("type")
    parser.add_argument("tags")
    parser.add_argument("-o", "--output-file", default="out/element.svg")


def add_render_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for render command."""
    parser.add_argument(
        "-i",
        "--input",
        dest="input_file_names",
        metavar="<path>",
        nargs="*",
        help="input XML file name or names (if not specified, file will be "
        "downloaded using the OpenStreetMap API)",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_file_name",
        metavar="<path>",
        default="out/map.svg",
        help="output SVG file name",
    )
    parser.add_argument(
        "-b",
        "--boundary-box",
        metavar="<lon1>,<lat1>,<lon2>,<lat2>",
        help="geo boundary box",
    )
    parser.add_argument(
        "--cache",
        help="path for temporary OSM files",
        default="cache",
        metavar="<path>",
    )
    parser.add_argument(
        "-z",
        "--zoom",
        type=float,
        metavar="<float>",
        help="OSM zoom level",
        default=18.0,
    )
    parser.add_argument(
        "-c",
        "--coordinates",
        metavar="<latitude>,<longitude>",
        help="coordinates of any location inside the tile",
    )
    parser.add_argument(
        "-s",
        "--size",
        metavar="<width>,<height>",
        help="resulted image size",
    )


def add_mapcss_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for mapcss command."""
    parser.add_argument(
        "--icons",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="add icons for nodes and areas",
    )
    parser.add_argument(
        "--ways",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="add style for ways and relations",
    )
    parser.add_argument(
        "--lifecycle",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="add icons for lifecycle tags; be careful: this will increase the "
        f"number of node and area selectors by {len(STAGES_OF_DECAY) + 1} "
        f"times",
    )
