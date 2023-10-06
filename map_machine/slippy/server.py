"""Map Machine tile server for slippy maps."""
import argparse
import logging
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Optional

import cairosvg

from map_machine.map_configuration import MapConfiguration
from map_machine.slippy.tile import Tile
from map_machine.workspace import workspace

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


class TileServerHandler(SimpleHTTPRequestHandler):
    """HTTP request handler that process sloppy map tile requests."""

    cache: Path = Path("cache")
    update_cache: bool = False
    options: Optional[argparse.Namespace] = None

    def __init__(
        self,
        request: bytes,
        client_address: tuple[str, int],
        server: HTTPServer,
    ) -> None:
        # TODO: delete?
        super().__init__(request, client_address, server)

    def do_GET(self) -> None:
        """Serve a GET request."""
        parts: list[str] = self.path.split("/")
        if not (len(parts) == 5 and not parts[0] and parts[1] == "tiles"):
            return

        zoom_level: int = int(parts[2])
        x: int = int(parts[3])
        y: int = int(parts[4])
        tile: Tile = Tile(x, y, zoom_level)
        tile_path: Path = workspace.get_tile_path()
        svg_path: Path = tile.get_file_name(tile_path)
        png_path: Path = svg_path.with_suffix(".png")

        if self.update_cache:
            if not png_path.exists():
                if not svg_path.exists():
                    tile.draw(
                        tile_path,
                        self.cache,
                        MapConfiguration(zoom_level=zoom_level),
                    )
                with svg_path.open(encoding="utf-8") as input_file:
                    cairosvg.svg2png(
                        file_obj=input_file, write_to=str(png_path)
                    )
                logging.info(f"SVG file is rasterized to {png_path}.")

        if png_path.exists():
            with png_path.open("rb") as input_file:
                self.send_response(200)
                self.send_header("Content-type", "image/png")
                self.end_headers()
                self.wfile.write(input_file.read())
                return


def run_server(options: argparse.Namespace) -> None:
    """Command-line interface for tile server."""
    server: Optional[HTTPServer] = None
    try:
        handler = TileServerHandler
        handler.cache = Path(options.cache)
        handler.update_cache = options.update_cache
        handler.options = options
        server = HTTPServer(("", options.port), handler)
        logging.info(f"Server started on port {options.port}.")
        server.serve_forever()
    finally:
        if server:
            server.socket.close()
