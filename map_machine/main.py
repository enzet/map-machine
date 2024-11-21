"""Map Machine entry point."""

import sys

if sys.version_info.major < 3 or sys.version_info.minor < 9:
    print(
        "FATAL Python "
        + str(sys.version_info.major)
        + "."
        + str(sys.version_info.minor)
        + " is not supported. Please, use at least Python 3.9."
    )
    print(
        "NOTE For Python 3.8 there is a special Map Machine branch `python3.8`."
    )
    sys.exit(1)

import argparse
import logging
from pathlib import Path

from map_machine.ui.cli import parse_arguments
from map_machine.workspace import Workspace

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def main() -> None:
    """Map Machine command-line entry point."""
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")

    logging.basicConfig(format="%(levelname)s %(message)s", level=logging.INFO)
    workspace: Workspace = Workspace(Path("out"))

    arguments: argparse.Namespace = parse_arguments(sys.argv)

    if not arguments.command:
        logging.fatal("No command provided. See --help.")

    elif arguments.command == "render":
        from map_machine import mapper

        mapper.render_map(arguments)

    elif arguments.command == "tile":
        from map_machine.slippy import tile

        tile.generate_tiles(arguments)

    elif arguments.command == "icons":
        from map_machine.pictogram.icon_collection import draw_icons

        draw_icons()

    elif arguments.command == "mapcss":
        from map_machine import mapcss

        mapcss.generate_mapcss(arguments)

    elif arguments.command == "draw":
        from map_machine.element.element import draw_element

        draw_element(arguments)

    elif arguments.command == "server":
        from map_machine.slippy import server

        server.run_server(arguments)

    elif arguments.command == "taginfo":
        from map_machine.scheme import Scheme
        from map_machine.doc.taginfo import write_taginfo_project_file

        write_taginfo_project_file(
            Scheme.from_file(workspace.DEFAULT_SCHEME_PATH)
        )


if __name__ == "__main__":
    main()
