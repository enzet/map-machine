"""
Tile generation.

See https://wiki.openstreetmap.org/wiki/Tiles
"""
import logging
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
from roentgen.osm_getter import get_osm, NetworkError
from roentgen.osm_reader import Map, OSMReader
from roentgen.raster import rasterize
from roentgen.scheme import Scheme
from roentgen.util import MinMax
from roentgen.ui import BoundaryBox


@dataclass
class Tiles:
    """
    Collection of tiles.
    """

    tiles: List["Tile"]
    tile_1: "Tile"
    tile_2: "Tile"
    scale: int
    boundary_box: BoundaryBox

    @classmethod
    def from_boundary_box(cls, boundary_box: BoundaryBox, scale: int):
        """Create minimal set of tiles that cover boundary box."""
        tiles: List["Tile"] = []
        tile_1 = Tile.from_coordinates(boundary_box.get_left_top(), scale)
        tile_2 = Tile.from_coordinates(boundary_box.get_right_bottom(), scale)

        for x in range(tile_1.x, tile_2.x + 1):
            for y in range(tile_1.y, tile_2.y + 1):
                tiles.append(Tile(x, y, scale))

        lat_2, lon_1 = tile_1.get_coordinates()
        lat_1, lon_2 = Tile(tile_2.x + 1, tile_2.y + 1, scale).get_coordinates()
        assert lon_2 > lon_1
        assert lat_2 > lat_1

        extended_boundary_box: BoundaryBox = BoundaryBox(
            lon_1, lat_1, lon_2, lat_2
        )
        return cls(tiles, tile_1, tile_2, scale, extended_boundary_box)

    def draw(self, directory: Path, cache_path: Path) -> None:
        """
        Draw set of tiles.

        :param directory: directory for tiles
        :param cache_path: directory for temporary OSM files
        """
        get_osm(self.boundary_box, cache_path)

        map_ = OSMReader().parse_osm_file(
            cache_path / (self.boundary_box.get_format_rounded() + ".osm")
        )
        for tile in self.tiles:
            file_path: Path = tile.get_file_name(directory)
            if not file_path.exists():
                tile.draw_for_map(map_, directory)

            output_path: Path = file_path.with_suffix(".png")
            if not output_path.exists():
                rasterize(file_path, output_path)

    def draw_image(self, cache_path: Path) -> None:
        """
        Draw all tiles as one picture.

        :param cache_path: directory for temporary SVG file and OSM files
        """
        output_path: Path = cache_path / (
            self.boundary_box.get_format_rounded() + ".svg"
        )
        if not output_path.exists():
            content = get_osm(self.boundary_box, cache_path)
            if not content:
                logging.error("Cannot download OSM data.")
                return None

            map_: Map = OSMReader().parse_osm_file(
                cache_path / (self.boundary_box.get_format_rounded() + ".osm")
            )
            lat_2, lon_1 = self.tile_1.get_coordinates()
            lat_1, lon_2 = Tile(
                self.tile_2.x + 1, self.tile_2.y + 1, self.scale
            ).get_coordinates()
            min_ = np.array((lat_1, lon_1))
            max_ = np.array((lat_2, lon_2))

            flinger: Flinger = Flinger(MinMax(min_, max_), self.scale)
            icon_extractor: ShapeExtractor = ShapeExtractor(
                workspace.ICONS_PATH, workspace.ICONS_CONFIG_PATH
            )
            scheme: Scheme = Scheme(workspace.DEFAULT_SCHEME_PATH)
            constructor: Constructor = Constructor(
                map_, flinger, scheme, icon_extractor
            )
            constructor.construct()

            svg: svgwrite.Drawing = svgwrite.Drawing(
                str(output_path), size=flinger.size
            )
            painter: Painter = Painter(
                map_=map_,
                flinger=flinger,
                svg=svg,
                icon_extractor=icon_extractor,
                scheme=scheme,
            )
            painter.draw(constructor)

            with output_path.open("w+") as output_file:
                svg.write(output_file)

        png_path: Path = (
            cache_path / f"{self.boundary_box.get_format_rounded()}.png"
        )
        if not png_path.exists():
            rasterize(output_path, png_path)


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

    def get_extended_boundary_box(self) -> BoundaryBox:
        """
        Same as get_boundary_box, but with extended boundaries.
        """
        point_1: np.array = self.get_coordinates()
        point_2: np.array = Tile(
            self.x + 1, self.y + 1, self.scale
        ).get_coordinates()

        # FIXME: check negative values

        lat_2 = int(point_1[0] * 1000) / 1000 + 0.002
        lon_1 = int(point_1[1] * 1000) / 1000 - 0.001
        lat_1 = int(point_2[0] * 1000) / 1000 - 0.001
        lon_2 = int(point_2[1] * 1000) / 1000 + 0.002

        return BoundaryBox(lon_1, lat_1, lon_2, lat_2)

    def load_map(self, cache_path: Path) -> Map:
        """
        Construct map data from extended boundary box.

        :param cache_path: directory to store OSM data files
        """
        boundary_box: BoundaryBox = self.get_extended_boundary_box()
        get_osm(boundary_box, cache_path)

        return OSMReader().parse_osm_file(
            cache_path / f"{boundary_box.format()}.osm"
        )

    def get_file_name(self, directory_name: Path) -> Path:
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

    def draw(self, directory_name: Path, cache_path: Path) -> None:
        """
        Draw tile to SVG file.

        :param directory_name: output directory to storing tiles
        :param cache_path: directory to store SVG and PNG tiles
        """
        try:
            map_: Map = self.load_map(cache_path)
        except NetworkError as e:
            raise NetworkError(f"Map doesn't loaded. {e.message}")

        self.draw_for_map(map_, directory_name)

    def draw_for_map(self, map_: Map, directory_name: Path) -> None:
        """Draw tile using existing map."""
        lat1, lon1 = self.get_coordinates()
        lat2, lon2 = Tile(self.x + 1, self.y + 1, self.scale).get_coordinates()

        min_: np.array = np.array((min(lat1, lat2), min(lon1, lon2)))
        max_: np.array = np.array((max(lat1, lat2), max(lon1, lon2)))

        flinger: Flinger = Flinger(MinMax(min_, max_), self.scale)
        size: np.array = flinger.size

        output_file_name: Path = self.get_file_name(directory_name)

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

    if options.coordinates:
        coordinates: List[float] = list(
            map(float, options.coordinates.strip().split(","))
        )
        tile: Tile = Tile.from_coordinates(np.array(coordinates), options.scale)
        try:
            tile.draw(directory, Path(options.cache))
        except NetworkError as e:
            logging.fatal(e.message)
    elif options.tile:
        scale, x, y = map(int, options.tile.split("/"))
        tile: Tile = Tile(x, y, scale)
        tile.draw(directory, Path(options.cache))
    elif options.boundary_box:
        boundary_box: Optional[BoundaryBox] = BoundaryBox.from_text(
            options.boundary_box
        )
        if boundary_box is None:
            sys.exit(1)
        tiles: Tiles = Tiles.from_boundary_box(boundary_box, options.scale)
        tiles.draw(directory, Path(options.cache))
        tiles.draw_image(Path(options.cache))
    else:
        logging.fatal("Specify either --coordinates, or --tile.")
        sys.exit(1)
