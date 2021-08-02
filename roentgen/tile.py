"""
Tile generation.

See https://wiki.openstreetmap.org/wiki/Tiles
"""
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import svgwrite

from roentgen import workspace
from roentgen.constructor import Constructor
from roentgen.flinger import Flinger
from roentgen.icon import ShapeExtractor
from roentgen.mapper import Painter
from roentgen.osm_getter import get_osm
from roentgen.osm_reader import Map, OSMReader
from roentgen.scheme import Scheme
from roentgen.ui import error
from roentgen.util import MinMax


@dataclass
class Tile:
    """
    OpenStreetMap tile, square bitmap graphics displayed in a grid arrangement
    to show a map.
    """

    x: int
    y: int
    scale: int

    @classmethod
    def from_coordinates(cls, coordinates: np.array, scale: int):
        """
        Code from https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames
        """
        lat_rad = np.radians(coordinates[0])
        n: float = 2.0 ** scale
        x: int = int((coordinates[1] + 180.0) / 360.0 * n)
        y: int = int((1.0 - np.arcsinh(np.tan(lat_rad)) / np.pi) / 2.0 * n)
        return cls(x, y, scale)

    def get_coordinates(self) -> np.array:
        """
        Return geo coordinates of the north-west corner of the tile.

        Code from https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames
        """
        n: float = 2.0 ** self.scale
        lon_deg: float = self.x / n * 360.0 - 180.0
        lat_rad: float = np.arctan(np.sinh(np.pi * (1 - 2 * self.y / n)))
        lat_deg: np.ndarray = np.degrees(lat_rad)
        return np.array((lat_deg, lon_deg))

    def get_boundary_box(self) -> Tuple[np.array, np.array]:
        """
        Get geographical boundary box of the tile: north-west and south-east
        points.
        """
        return (
            self.get_coordinates(),
            Tile(self.x + 1, self.y + 1, self.scale).get_coordinates(),
        )

    def get_extended_boundary_box(self) -> Tuple[np.array, np.array]:
        """
        Same as get_boundary_box, but with extended boundaries.
        """
        point_1: np.array = self.get_coordinates()
        point_2: np.array = Tile(
            self.x + 1, self.y + 1, self.scale
        ).get_coordinates()

        extended_1: Tuple[float, float] = (
            int(point_1[0] * 1000) / 1000 + 0.002,
            int(point_1[1] * 1000) / 1000 - 0.001,
        )
        extended_2: Tuple[float, float] = (
            int(point_2[0] * 1000) / 1000 - 0.001,
            int(point_2[1] * 1000) / 1000 + 0.002,
        )
        return np.array(extended_1), np.array(extended_2)

    def load_map(self, cache_path: Path) -> Optional[Map]:
        """
        Construct map data from extended boundary box.
        """
        coordinates_1, coordinates_2 = self.get_extended_boundary_box()
        lat1, lon1 = coordinates_1
        lat2, lon2 = coordinates_2

        boundary_box: str = (
            f"{min(lon1, lon2):.3f},{min(lat1, lat2):.3f},"
            f"{max(lon1, lon2):.3f},{max(lat1, lat2):.3f}"
        )
        content = get_osm(boundary_box, cache_path)
        if not content:
            error("cannot download OSM data")
            return None

        return OSMReader().parse_osm_file(cache_path / (boundary_box + ".osm"))

    def get_map_name(self, directory_name: Path) -> Path:
        """
        Get tile output SVG file path.
        """
        return directory_name / f"tile_{self.scale}_{self.x}_{self.y}.svg"

    def get_carto_address(self) -> str:
        """
        Get URL of this tile from the OpenStreetMap server.
        """
        return (
            f"https://tile.openstreetmap.org/{self.scale}/{self.x}/{self.y}.png"
        )

    def draw(self, directory_name: Path, cache_path: Path):
        """
        Draw tile to SVG file.

        :param directory_name: output directory to storing tiles
        """
        map_ = self.load_map(cache_path)

        lat1, lon1 = self.get_coordinates()
        lat2, lon2 = Tile(self.x + 1, self.y + 1, self.scale).get_coordinates()

        min_: np.array = np.array((min(lat1, lat2), min(lon1, lon2)))
        max_: np.array = np.array((max(lat1, lat2), max(lon1, lon2)))

        flinger: Flinger = Flinger(MinMax(min_, max_), self.scale)
        size: np.array = flinger.size

        output_file_name: Path = self.get_map_name(directory_name)

        svg: svgwrite.Drawing = svgwrite.Drawing(
            str(output_file_name), size=size
        )
        icon_extractor: ShapeExtractor = ShapeExtractor(
            workspace.ICONS_PATH, workspace.ICONS_CONFIG_PATH
        )
        scheme: Scheme = Scheme(workspace.DEFAULT_SCHEME_PATH)
        constructor: Constructor = Constructor(
            map_, flinger, scheme, icon_extractor
        )
        constructor.construct()

        painter: Painter = Painter(
            map_=map_,
            flinger=flinger,
            svg=svg,
            icon_extractor=icon_extractor,
            scheme=scheme,
        )
        painter.draw(constructor)

        print(f"Writing output SVG {output_file_name}...")
        with output_file_name.open("w") as output_file:
            svg.write(output_file)


def ui(options) -> None:
    """
    Simple user interface for tile generation.
    """
    directory: Path = workspace.get_tile_path()

    tile: Tile
    if options.c and options.s:
        coordinates: List[float] = list(map(float, options.c.split(",")))
        tile = Tile.from_coordinates(np.array(coordinates), int(options.s))
    elif options.t:
        scale, x, y = map(int, options.t.split("/"))
        tile = Tile(x, y, scale)
    else:
        sys.exit(1)

    tile.draw(directory, Path(options.cache))
    print(tile.get_carto_address())
