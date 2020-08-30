"""
Author: Sergey Vartanov (me@enzet.ru).
"""
import argparse
import sys

from typing import Optional


def parse_options(args):
    """
    Parse Röntgen command-line options.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-i", "--input",
        dest="input_file_name",
        metavar="<path>",
        nargs="*",
        help="input XML file name (if not specified, file will be downloaded "
             "using OpenStreetMap API)")
    parser.add_argument(
        "-o", "--output",
        dest="output_file_name",
        metavar="<path>",
        default="map.svg",
        help="output SVG file name (map.svg by default)")
    parser.add_argument(
        "-b", "--boundary-box",
        dest="boundary_box",
        metavar="<lon1>,<lat1>,<lon2>,<lat2>",
        help="geo boundary box, use \"m\" instead of \"-\" for negative values",
        required=True)
    parser.add_argument(
        "-s", "--size",
        metavar="<width>,<height>",
        help="output SVG file size in pixels",
        dest="size")
    parser.add_argument(
        "-nn", "--no-draw-nodes",
        dest="draw_nodes",
        action="store_false",
        default=True)
    parser.add_argument(
        "-nw", "--no-draw-ways", dest="draw_ways", action="store_false",
        default=True)
    parser.add_argument(
        "--captions", "--no-draw-captions", dest="draw_captions",
        default="main")
    parser.add_argument(
        "--show-missing-tags", dest="show_missing_tags", action="store_true")
    parser.add_argument(
        "--no-show-missing-tags", dest="show_missing_tags",
        action="store_false")
    parser.add_argument("--overlap", dest="overlap", default=12, type=int)
    parser.add_argument(
        "--show-index", dest="show_index", action="store_true")
    parser.add_argument(
        "--no-show-index", dest="show_index", action="store_false")
    parser.add_argument("--mode", default="normal")
    parser.add_argument("--seed", default="")
    parser.add_argument("--level", default=None)

    arguments = parser.parse_args(args[1:])

    if arguments.boundary_box:
        arguments.boundary_box = arguments.boundary_box.replace("m", "-")

    return arguments


def write_line(number, total):
    length = 20
    parts = length * 8
    boxes = [" ", "▏", "▎", "▍", "▌", "▋", "▊", "▉"]

    if number == -1:
        print("%3s" % "100" + " % █" + (length * "█") + "█")
    elif number % 1000 == 0:
        p = number / float(total)
        l = int(p * parts)
        fl = int(l / 8)
        pr = int(l - fl * 8)
        print(("%3s" % str(int(p * 1000) / 10)) + " % █" + (fl * "█") +
            boxes[pr] + ((length - fl - 1) * " ") + "█")
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
