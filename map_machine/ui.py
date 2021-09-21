"""
Command-line user interface.
"""
import argparse
import sys
from typing import Dict, List

from map_machine import __version__
from map_machine.map_configuration import BuildingMode, DrawingMode, LabelMode
from map_machine.osm_reader import STAGES_OF_DECAY

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

BOXES: str = " ▏▎▍▌▋▊▉"
BOXES_LENGTH: int = len(BOXES)

COMMANDS: Dict[str, List[str]] = {
    "render": ["render", "-b", "10.000,20.000,10.001,20.001"],
    "render_with_tooltips": [
        "render",
        "-b",
        "10.000,20.000,10.001,20.001",
        "--show-tooltips",
    ],
    "icons": ["icons"],
    "mapcss": ["mapcss"],
    "element": ["element", "--node", "amenity=bench,material=wood"],
    "tile": ["tile", "--coordinates", "50.000,40.000"],
}


def parse_arguments(args: List[str]) -> argparse.Namespace:
    """Parse Map Machine command-line arguments."""
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

    render_parser = subparser.add_parser("render", help="draw SVG map")
    add_render_arguments(render_parser)
    add_map_arguments(render_parser)

    tile_parser = subparser.add_parser(
        "tile", help="generate PNG tiles for slippy maps"
    )
    add_tile_arguments(tile_parser)
    add_map_arguments(tile_parser)

    add_server_arguments(subparser.add_parser("server", help="run tile server"))
    add_element_arguments(
        subparser.add_parser(
            "element", help="draw OSM element: node, way, relation"
        )
    )
    add_mapcss_arguments(
        subparser.add_parser("mapcss", help="write MapCSS file")
    )

    subparser.add_parser("icons", help="draw icons")
    subparser.add_parser("taginfo", help="write Taginfo JSON file")

    arguments: argparse.Namespace = parser.parse_args(args[1:])

    return arguments


def add_map_arguments(parser: argparse.ArgumentParser) -> None:
    """Add map-specific arguments."""
    parser.add_argument(
        "--buildings",
        metavar="<mode>",
        default="flat",
        choices=(x.value for x in BuildingMode),
        help="building drawing mode: "
        + ", ".join(x.value for x in BuildingMode),
    )
    parser.add_argument(
        "--mode",
        default="normal",
        metavar="<string>",
        choices=(x.value for x in DrawingMode),
        help="map drawing mode: " + ", ".join(x.value for x in DrawingMode),
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
        choices=(x.value for x in LabelMode),
        help="label drawing mode: " + ", ".join(x.value for x in LabelMode),
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
        "--show-tooltips",
        help="add tooltips with tags for icons in SVG files",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--no-show-tooltips",
        dest="show_tooltips",
        help="don't add tooltips with tags for icons in SVG files",
        action="store_false",
    )
    parser.add_argument(
        "--country",
        help="two-letter code (ISO 3166-1 alpha-2) of country, that should be "
        "used for location restrictions",
        default="world",
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
        help="construct the minimum amount of tiles that cover requested "
        "boundary box",
        metavar="<lon1>,<lat1>,<lon2>,<lat2>",
    )
    parser.add_argument(
        "-z",
        "--zoom",
        type=str,
        metavar="<integer>",
        help="OSM zoom levels; can be list of numbers or ranges, e.g. `16-18`, "
        "`16,17,18`, or `16,18-20`",
        default="18",
    )
    parser.add_argument(
        "-i",
        "--input",
        dest="input_file_name",
        metavar="<path>",
        help="input OSM XML file name (if not specified, file will be "
        "downloaded using OpenStreetMap API)",
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


def add_element_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for element command."""
    parser.add_argument("-n", "--node")
    parser.add_argument("-w", "--way")
    parser.add_argument("-r", "--relation")


def add_render_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for render command."""
    parser.add_argument(
        "-i",
        "--input",
        dest="input_file_names",
        metavar="<path>",
        nargs="*",
        help="input XML file name or names (if not specified, file will be "
        "downloaded using OpenStreetMap API)",
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
        help="geo boundary box; if first value is negative, enclose the value "
        "with quotes and use space before `-`",
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
        type=int,
        metavar="<integer>",
        help="OSM zoom level",
        default=18,
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
        action="store_true",
        default=True,
        help="add icons for nodes and areas",
    )
    parser.add_argument(
        "--no-icons",
        dest="icons",
        action="store_false",
        help="don't add icons for nodes and areas",
    )
    parser.add_argument(
        "--ways",
        action="store_true",
        default=False,
        help="add style for ways and relations",
    )
    parser.add_argument(
        "--no-ways",
        dest="ways",
        action="store_false",
        help="don't add style for ways and relations",
    )
    parser.add_argument(
        "--lifecycle",
        action="store_true",
        default=True,
        help="add icons for lifecycle tags; be careful: this will increase the "
        f"number of node and area selectors by {len(STAGES_OF_DECAY) + 1} "
        f"times",
    )
    parser.add_argument(
        "--no-lifecycle",
        dest="lifecycle",
        action="store_false",
        help="don't add icons for lifecycle tags",
    )


def progress_bar(
    number: int, total: int, length: int = 20, step: int = 1000, text: str = ""
) -> None:
    """
    Draw progress bar using Unicode symbols.

    :param number: current value
    :param total: maximum value
    :param length: progress bar length.
    :param step: frequency of progress bar updating (assuming that numbers go
        subsequently)
    :param text: short description
    """
    if number == -1:
        sys.stdout.write(f"100 % {length * '█'}▏{text}\n")
    elif number % step == 0:
        ratio: float = number / total
        parts: int = int(ratio * length * BOXES_LENGTH)
        fill_length: int = int(parts / BOXES_LENGTH)
        box: str = BOXES[int(parts - fill_length * BOXES_LENGTH)]
        sys.stdout.write(
            f"{str(int(int(ratio * 1000) / 10)):>3} % {fill_length * '█'}{box}"
            f"{int(length - fill_length - 1) * ' '}▏{text}\n\033[F"
        )
