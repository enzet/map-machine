"""
Röntgen tile server for slippy maps.
"""
import argparse
import logging
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Optional

import cairosvg

from roentgen.tile import Tile
from roentgen.workspace import workspace

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


class _Handler(SimpleHTTPRequestHandler):
    """
    HTTP request handler that process sloppy map tile requests.
    """

    cache: Path = Path("cache")
    update_cache: bool = False
    options = None

    def __init__(
        self,
        request: bytes,
        client_address: tuple[str, int],
        server: HTTPServer,
    ) -> None:
        super().__init__(request, client_address, server)

    def do_GET(self) -> None:
        """Serve a GET request."""
        parts: list[str] = self.path.split("/")
        if not (len(parts) == 5 and not parts[0] and parts[1] == "tiles"):
            return

        zoom_level: int = int(parts[2])
        x: int = int(parts[3])
        y: int = int(parts[4])
        tile_path: Path = workspace.get_tile_path()
        png_path: Path = tile_path / f"tile_{zoom_level}_{x}_{y}.png"

        if self.update_cache:
            svg_path: Path = png_path.with_suffix(".svg")
            if not png_path.exists():
                if not svg_path.exists():
                    tile = Tile(x, y, zoom_level)
                    tile.draw(tile_path, self.cache, self.options)
                with svg_path.open() as input_file:
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


def ui(options: argparse.Namespace) -> None:
    """Command-line interface for tile server."""
    server: Optional[HTTPServer] = None
    try:
        port: int = 8080
        handler = _Handler
        handler.cache = Path(options.cache)
        handler.options = options
        server: HTTPServer = HTTPServer(("", port), handler)
        logging.info(f"Server started on port {port}.")
        server.serve_forever()
    finally:
        if server:
            server.socket.close()
