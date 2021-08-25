"""
Command-line user interface.
"""
import argparse
import sys

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

from enum import Enum

from roentgen.osm_reader import STAGES_OF_DECAY

BOXES: str = " ▏▎▍▌▋▊▉"
BOXES_LENGTH: int = len(BOXES)

AUTHOR_MODE: str = "author"
TIME_MODE: str = "time"


class BuildingMode(Enum):
    """
    Building drawing mode.
    """

    FLAT = "flat"
    ISOMETRIC = "isometric"
    ISOMETRIC_NO_PARTS = "isometric-no-parts"


def parse_options(args) -> argparse.Namespace:
    """Parse Röntgen command-line options."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Röntgen. OpenStreetMap renderer with custom icon set"
    )
    subparser = parser.add_subparsers(dest="command")

    tile_parser = subparser.add_parser("tile")
    add_tile_arguments(tile_parser)
    add_map_arguments(tile_parser)

    render_parser = subparser.add_parser("render")
    add_render_arguments(render_parser)
    add_map_arguments(render_parser)

    add_server_arguments(subparser.add_parser("server"))
    add_element_arguments(subparser.add_parser("element"))
    add_mapcss_arguments(subparser.add_parser("mapcss"))

    subparser.add_parser("icons")
    subparser.add_parser("taginfo")

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
        help="map drawing mode",
        metavar="<string>",
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
        help="label drawing mode: `no`, `main`, or `all`",
        dest="label_mode",
        default="main",
        metavar="<string>",
    )
    parser.add_argument(
        "-s",
        "--scale",
        type=int,
        metavar="<integer>",
        help="OSM zoom level",
        default=18,
    )
    parser.add_argument(
        "--level",
        default="overground",
        help="display only this floor level",
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
        metavar="<scale>/<x>/<y>",
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


def add_server_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for server command."""
    parser.add_argument(
        "--cache",
        help="path for temporary OSM files",
        default="cache",
        metavar="<path>",
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
        dest="input_file_name",
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
        "--seed",
        default="",
        help="seed for random",
        metavar="<string>",
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
        print(f"100 % {length * '█'}▏{text}")
    elif number % step == 0:
        ratio: float = number / total
        parts: int = int(ratio * length * BOXES_LENGTH)
        fill_length: int = int(parts / BOXES_LENGTH)
        box: str = BOXES[int(parts - fill_length * BOXES_LENGTH)]
        print(
            f"{str(int(int(ratio * 1000) / 10)):>3} % {fill_length * '█'}{box}"
            f"{int(length - fill_length - 1) * ' '}▏{text}"
        )
        sys.stdout.write("\033[F")
