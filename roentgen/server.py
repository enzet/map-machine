import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional

from roentgen.workspace import workspace
from roentgen.raster import rasterize
from roentgen.tile import Tile

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


class Handler(BaseHTTPRequestHandler):

    update_cache: bool = False

    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server)
        self.cache: Path = Path("cache")

    def write(self, message):
        if isinstance(message, bytes):
            self.wfile.write(message)
        else:
            self.wfile.write(message.encode("utf-8"))

    def do_GET(self):
        parts = self.path.split("/")
        if not (len(parts) == 5 and not parts[0] and parts[1] == "tiles"):
            return
        zoom = int(parts[2])
        x = int(parts[3])
        y = int(parts[4])
        tile_path: Path = workspace.get_tile_path()
        png_path = tile_path / f"tile_{zoom}_{x}_{y}.png"
        if self.update_cache:
            svg_path = tile_path / f"tile_{zoom}_{x}_{y}.svg"
            if not png_path.exists():
                if not svg_path.exists():
                    tile = Tile(x, y, zoom)
                    tile.draw(tile_path, self.cache)
                rasterize(svg_path, png_path)
        if zoom != 18:
            return
        if png_path.exists():
            with png_path.open("rb") as input_file:
                self.send_response(200)
                self.send_header("Content-type", "image/png")
                self.end_headers()
                self.write(input_file.read())
                return


def ui(options):
    server: Optional[HTTPServer] = None
    try:
        port: int = 8080
        server = HTTPServer(("", port), Handler)
        server.cache_path = Path(options.cache)
        server.serve_forever()
        logging.info(f"Server started on port {port}.")
    finally:
        if server:
            server.socket.close()
