"""Map Machine tile server for slippy maps."""

from __future__ import annotations

import logging
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import TYPE_CHECKING

import cairosvg

from map_machine.map_configuration import MapConfiguration
from map_machine.scheme import Scheme
from map_machine.slippy.tile import Tile
from map_machine.workspace import workspace

if TYPE_CHECKING:
    import argparse

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

logger: logging.Logger = logging.getLogger(__name__)

GET_REQUEST_PARTS: list[str] = ["address", "tiles", "zoom_level", "x", "y"]


class TileServerHandler(SimpleHTTPRequestHandler):
    """HTTP request handler that process sloppy map tile requests."""

    cache: Path = Path("cache")
    update_cache: bool = False
    options: argparse.Namespace | None = None

    def __init__(
        self,
        request: bytes,
        client_address: tuple[str, int],
        server: HTTPServer,
    ) -> None:
        super().__init__(request, client_address, server)

        if not self.cache.exists():
            message: str = (
                f"Cache directory `{self.cache}` for server does not exist, "
                "please create it."
            )
            logger.fatal(message)
            sys.exit(1)

    def do_GET(self) -> None:
        """Serve a GET request."""
        parts: list[str] = self.path.split("/")

        if not (
            len(parts) == len(GET_REQUEST_PARTS)
            and not parts[GET_REQUEST_PARTS.index("request")]
            and parts[GET_REQUEST_PARTS.index("tiles")] == "tiles"
        ):
            return

        zoom_level: int = int(parts[GET_REQUEST_PARTS.index("zoom_level")])
        x: int = int(parts[GET_REQUEST_PARTS.index("x")])
        y: int = int(parts[GET_REQUEST_PARTS.index("y")])
        tile: Tile = Tile(x, y, zoom_level)
        tile_path: Path = workspace.get_tile_path()
        svg_path: Path = tile.get_file_name(tile_path)
        png_path: Path = svg_path.with_suffix(".png")

        if self.update_cache and not png_path.exists():
            if not svg_path.exists():
                scheme = Scheme.from_file(
                    workspace.DEFAULT_SCHEME_PATH
                    if self.options.scheme == "default"
                    else Path(self.options.scheme)
                )
                tile.draw(
                    tile_path,
                    self.cache,
                    MapConfiguration.from_options(
                        scheme,
                        self.options,
                        zoom_level,
                    ),
                )
            with svg_path.open(encoding="utf-8") as input_file:
                cairosvg.svg2png(file_obj=input_file, write_to=str(png_path))
            logger.info("SVG file is rasterized to `%s`.", png_path)

        if png_path.exists():
            with png_path.open("rb") as input_file:
                self.send_response(200)
                self.send_header("Content-type", "image/png")
                self.end_headers()
                self.wfile.write(input_file.read())
                return


def run_server(options: argparse.Namespace) -> None:
    """Command-line interface for tile server."""
    server: HTTPServer | None = None
    try:
        handler = TileServerHandler
        handler.cache = Path(options.cache)
        handler.update_cache = options.update_cache
        handler.options = options
        server = HTTPServer(("", options.port), handler)
        logger.info("Server started on port %s.", options.port)
        server.serve_forever()
    finally:
        if server:
            server.socket.close()
