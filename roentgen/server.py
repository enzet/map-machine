"""
Röntgen tile server for sloppy maps.
"""
import logging
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional

import cairosvg

from roentgen.tile import Tile
from roentgen.workspace import workspace

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


class Handler(SimpleHTTPRequestHandler):
    """
    HTTP request handler that process sloppy map tile requests.
    """

    cache: Path = Path("cache")
    update_cache: bool = False

    def __init__(
        self, request: bytes, client_address: tuple[str, int], server
    ) -> None:
        super().__init__(request, client_address, server)

    def do_GET(self) -> None:
        """Serve a GET request."""
        parts: list[str] = self.path.split("/")
        if not (len(parts) == 5 and not parts[0] and parts[1] == "tiles"):
            return
        zoom: int = int(parts[2])
        x: int = int(parts[3])
        y: int = int(parts[4])
        tile_path: Path = workspace.get_tile_path()
        png_path = tile_path / f"tile_{zoom}_{x}_{y}.png"
        if self.update_cache:
            svg_path = tile_path / f"tile_{zoom}_{x}_{y}.svg"
            if not png_path.exists():
                if not svg_path.exists():
                    tile = Tile(x, y, zoom)
                    tile.draw(tile_path, self.cache)
                with svg_path.open() as input_file:
                    cairosvg.svg2png(
                        file_obj=input_file, write_to=str(png_path)
                    )
                logging.info(f"SVG file is rasterized to {png_path}.")
        if zoom != 18:
            return
        if png_path.exists():
            with png_path.open("rb") as input_file:
                self.send_response(200)
                self.send_header("Content-type", "image/png")
                self.end_headers()
                self.wfile.write(input_file.read())
                return


def ui(options) -> None:
    """Command-line interface for tile server."""
    server: Optional[HTTPServer] = None
    try:
        port: int = 8080
        handler = Handler
        handler.cache = Path(options.cache)
        server: HTTPServer = HTTPServer(("", port), handler)
        server.serve_forever()
        logging.info(f"Server started on port {port}.")
    finally:
        if server:
            server.socket.close()
