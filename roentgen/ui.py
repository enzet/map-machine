"""
Command-line user interface.
"""
import argparse
import re
import sys

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

import logging
from dataclasses import dataclass

import numpy as np

from roentgen.osm_reader import STAGES_OF_DECAY

BOXES: str = " ▏▎▍▌▋▊▉"
BOXES_LENGTH: int = len(BOXES)

AUTHOR_MODE: str = "author"
TIME_MODE: str = "time"

LATITUDE_MAX_DIFFERENCE: float = 0.5
LONGITUDE_MAX_DIFFERENCE: float = 0.5


def parse_options(args) -> argparse.Namespace:
    """Parse Röntgen command-line options."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Röntgen. OpenStreetMap renderer with custom icon set"
    )
    subparser = parser.add_subparsers(dest="command")

    add_render_arguments(subparser.add_parser("render"))
    add_tile_arguments(subparser.add_parser("tile"))
    add_server_arguments(subparser.add_parser("server"))
    add_element_arguments(subparser.add_parser("element"))
    add_mapcss_arguments(subparser.add_parser("mapcss"))

    subparser.add_parser("icons")
    subparser.add_parser("taginfo")

    arguments: argparse.Namespace = parser.parse_args(args[1:])

    return arguments


def add_tile_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for tile command."""
    parser.add_argument(
        "-c",
        "--coordinates",
        metavar="<latitude>,<longitude>",
        help="coordinates of any location inside the tile",
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
        "-s",
        "--scale",
        metavar="<float>",
        help="OSM zoom level (may not be integer)",
        default=18,
        type=float,
    )
    parser.add_argument(
        "--cache",
        help="path for temporary OSM files",
        default="cache",
        metavar="<path>",
    )
    parser.add_argument(
        "--labels",
        help="label drawing mode: `no`, `main`, or `all`",
        dest="label_mode",
        default="main",
    )
    parser.add_argument(
        "--overlap",
        dest="overlap",
        default=12,
        type=int,
        help="how many pixels should be left around icons and text",
    )
    parser.add_argument(
        "--mode",
        default="normal",
        help="map drawing mode",
    )
    parser.add_argument(
        "--seed",
        default="",
        help="seed for random",
    )
    parser.add_argument(
        "--level",
        default=None,
        help="display only this floor level",
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
        default=True,
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


@dataclass
class BoundaryBox:
    """
    Rectangle that limit space on the map.
    """

    left: float
    bottom: float
    right: float
    top: float

    @classmethod
    def from_text(cls, boundary_box: str):
        """
        Parse boundary box string representation.

        Note, that:
            left < right
            bottom < top

        :param boundary_box: boundary box string representation in the form of
            <longitude 1>,<latitude 1>,<longitude 2>,<latitude 2> or simply
            <left>,<bottom>,<right>,<top>.
        """
        boundary_box = boundary_box.replace(" ", "")

        matcher = re.match(
            "(?P<left>[0-9.-]*),(?P<bottom>[0-9.-]*),"
            + "(?P<right>[0-9.-]*),(?P<top>[0-9.-]*)",
            boundary_box,
        )

        if not matcher:
            logging.fatal("Invalid boundary box.")
            return None

        try:
            left: float = float(matcher.group("left"))
            bottom: float = float(matcher.group("bottom"))
            right: float = float(matcher.group("right"))
            top: float = float(matcher.group("top"))
        except ValueError:
            logging.fatal("Invalid boundary box.")
            return None

        if left >= right:
            logging.fatal("Negative horizontal boundary.")
            return None
        if bottom >= top:
            logging.error("Negative vertical boundary.")
            return None
        if (
            right - left > LONGITUDE_MAX_DIFFERENCE
            or top - bottom > LATITUDE_MAX_DIFFERENCE
        ):
            logging.error("Boundary box is too big.")
            return None

        return cls(left, bottom, right, top)

    def get_left_top(self) -> (np.array, np.array):
        """Get left top corner of the boundary box."""
        return self.top, self.left

    def get_right_bottom(self) -> (np.array, np.array):
        """Get right bottom corner of the boundary box."""
        return self.bottom, self.right

    def round(self) -> "BoundaryBox":
        """Round boundary box."""
        self.left = round(self.left * 1000) / 1000 - 0.001
        self.bottom = round(self.bottom * 1000) / 1000 - 0.001
        self.right = round(self.right * 1000) / 1000 + 0.001
        self.top = round(self.top * 1000) / 1000 + 0.001

        return self

    def get_format(self) -> str:
        """
        Get text representation of the boundary box:
        <longitude 1>,<latitude 1>,<longitude 2>,<latitude 2>.  Coordinates are
        rounded to three digits after comma.
        """
        return (
            f"{self.left:.3f},{self.bottom:.3f},{self.right:.3f},{self.top:.3f}"
        )
