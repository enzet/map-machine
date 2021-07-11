"""
Command-line user interface.
"""
import argparse
import sys

from typing import List, Optional

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

BOXES: List[str] = [" ", "▏", "▎", "▍", "▌", "▋", "▊", "▉"]
BOXES_LENGTH: int = len(BOXES)

AUTHOR_MODE: str = "author"
TIME_MODE: str = "time"


def parse_options(args) -> argparse.Namespace:
    """
    Parse Röntgen command-line options.
    """
    parser = argparse.ArgumentParser(
        description="Röntgen. OpenStreetMap renderer with custom icon set"
    )
    subparser = parser.add_subparsers(dest="command")

    render = subparser.add_parser("render")
    icons = subparser.add_parser("icons")
    mapcss = subparser.add_parser("mapcss")
    tile = subparser.add_parser("tile")

    render.add_argument(
        "-i",
        "--input",
        dest="input_file_name",
        metavar="<path>",
        nargs="*",
        help="input XML file name or names (if not specified, file will be "
        "downloaded using OpenStreetMap API)",
    )
    render.add_argument(
        "-o",
        "--output",
        dest="output_file_name",
        metavar="<path>",
        default="out/map.svg",
        help="output SVG file name (out/map.svg by default)",
    )
    render.add_argument(
        "-b",
        "--boundary-box",
        metavar="<lon1>,<lat1>,<lon2>,<lat2>",
        help='geo boundary box, use space before "-" if the first value is '
        "negative",
    )
    render.add_argument(
        "-s",
        "--scale",
        metavar="<float>",
        help="OSM zoom level (may not be integer, default is 18)",
        default=18,
        type=float,
    )
    render.add_argument(
        "--cache",
        help="path for temporary OSM files",
        default="cache",
        metavar="<path>",
    )
    render.add_argument(
        "--labels",
        help="label drawing mode: `no`, `main`, or `all`",
        dest="label_mode",
        default="main",
    )
    render.add_argument(
        "--overlap",
        dest="overlap",
        default=12,
        type=int,
        help="how many pixels should be left around icons and text",
    )
    render.add_argument("--mode", default="normal")
    render.add_argument("--seed", default="")
    render.add_argument("--level", default=None)

    tile.add_argument("-c")
    tile.add_argument("-s")
    tile.add_argument("-t")
    tile.add_argument(
        "--cache",
        help="path for temporary OSM files",
        default="cache",
        metavar="<path>",
    )

    arguments: argparse.Namespace = parser.parse_args(args[1:])

    return arguments


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


def error(message: Optional[str] = None):
    """
    Print error message.

    :param message: message to print.
    """
    if message:
        print(f"Error: {message}.")
    else:
        print("Error.")
