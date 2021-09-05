"""
Röntgen entry point.
"""
import argparse
import logging
import sys
from pathlib import Path

from roentgen.ui import parse_options
from roentgen.workspace import Workspace

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def main() -> None:
    """Röntgen command-line entry point."""
    logging.basicConfig(format="%(levelname)s %(message)s", level=logging.INFO)
    workspace: Workspace = Workspace(Path("out"))

    arguments: argparse.Namespace = parse_options(sys.argv)

    if not arguments.command:
        print("No command provided. See --help.")

    elif arguments.command == "render":
        from roentgen import mapper

        mapper.ui(arguments)

    elif arguments.command == "tile":
        from roentgen import tile

        tile.ui(arguments)

    elif arguments.command == "icons":
        from roentgen.grid import draw_icons

        draw_icons()

    elif arguments.command == "mapcss":
        from roentgen import mapcss

        mapcss.ui(arguments)

    elif arguments.command == "element":
        from roentgen.element import draw_element

        draw_element(arguments)

    elif arguments.command == "server":
        from roentgen import server

        server.ui(arguments)

    elif arguments.command == "taginfo":
        from roentgen.scheme import Scheme
        from roentgen.taginfo import write_taginfo_project_file

        write_taginfo_project_file(Scheme(workspace.DEFAULT_SCHEME_PATH))


if __name__ == "__main__":
    main()
