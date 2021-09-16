"""
Map Machine entry point.
"""
import argparse
import logging
import sys
from pathlib import Path

from map_machine.ui import parse_arguments
from map_machine.workspace import Workspace

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def main() -> None:
    """Map Machine command-line entry point."""
    logging.basicConfig(format="%(levelname)s %(message)s", level=logging.INFO)
    workspace: Workspace = Workspace(Path("out"))

    arguments: argparse.Namespace = parse_arguments(sys.argv)

    if not arguments.command:
        logging.fatal("No command provided. See --help.")

    elif arguments.command == "render":
        from map_machine import mapper

        mapper.ui(arguments)

    elif arguments.command == "tile":
        from map_machine import tile

        tile.ui(arguments)

    elif arguments.command == "icons":
        from map_machine.grid import draw_icons

        draw_icons()

    elif arguments.command == "mapcss":
        from map_machine import mapcss

        mapcss.ui(arguments)

    elif arguments.command == "element":
        from map_machine.element import draw_element

        draw_element(arguments)

    elif arguments.command == "server":
        from map_machine import server

        server.ui(arguments)

    elif arguments.command == "taginfo":
        from map_machine.scheme import Scheme
        from map_machine.taginfo import write_taginfo_project_file

        write_taginfo_project_file(Scheme(workspace.DEFAULT_SCHEME_PATH))


if __name__ == "__main__":
    main()
