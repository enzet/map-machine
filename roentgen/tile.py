"""
Tile generation.

See https://wiki.openstreetmap.org/wiki/Tiles
"""
import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cairosvg
import numpy as np
import svgwrite
from PIL import Image

from roentgen.constructor import Constructor
from roentgen.flinger import Flinger
from roentgen.icon import ShapeExtractor
from roentgen.mapper import Map
from roentgen.map_configuration import MapConfiguration
from roentgen.osm_getter import NetworkError, get_osm
from roentgen.osm_reader import OSMData, OSMReader
from roentgen.scheme import Scheme
from roentgen.boundary_box import BoundaryBox
from roentgen.workspace import workspace

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

TILE_WIDTH, TILE_HEIGHT = 256, 256


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
    def from_coordinates(cls, coordinates: np.ndarray, scale: int) -> "Tile":
        """
        Code from https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames

        :param coordinates: any coordinates inside tile
        :param scale: OpenStreetMap zoom level
        """
        lat_rad: np.ndarray = np.radians(coordinates[0])
        n: float = 2.0 ** scale
        x: int = int((coordinates[1] + 180.0) / 360.0 * n)
        y: int = int((1.0 - np.arcsinh(np.tan(lat_rad)) / np.pi) / 2.0 * n)
        return cls(x, y, scale)

    def get_coordinates(self) -> np.ndarray:
        """
        Return geo coordinates of the north-west corner of the tile.

        Code from https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames
        """
        n: float = 2.0 ** self.scale
        lon_deg: float = self.x / n * 360.0 - 180.0
        lat_rad: float = np.arctan(np.sinh(np.pi * (1 - 2 * self.y / n)))
        lat_deg: np.ndarray = np.degrees(lat_rad)
        return np.array((lat_deg, lon_deg))

    def get_boundary_box(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Get geographical boundary box of the tile: north-west and south-east
        points.
        """
        return (
            self.get_coordinates(),
            Tile(self.x + 1, self.y + 1, self.scale).get_coordinates(),
        )

    def get_extended_boundary_box(self) -> BoundaryBox:
        """Same as get_boundary_box, but with extended boundaries."""
        point_1: np.ndarray = self.get_coordinates()
        point_2: np.ndarray = Tile(
            self.x + 1, self.y + 1, self.scale
        ).get_coordinates()

        return BoundaryBox(
            point_1[1], point_2[0], point_2[1], point_1[0]
        ).round()

    def load_osm_data(self, cache_path: Path) -> OSMData:
        """
        Construct map data from extended boundary box.

        :param cache_path: directory to store OSM data files
        """
        cache_file_path: Path = (
            cache_path / f"{self.get_extended_boundary_box().get_format()}.osm"
        )
        get_osm(self.get_extended_boundary_box(), cache_file_path)

        return OSMReader().parse_osm_file(cache_file_path)

    def get_file_name(self, directory_name: Path) -> Path:
        """Get tile output SVG file path."""
        return directory_name / f"tile_{self.scale}_{self.x}_{self.y}.svg"

    def exists(self, directory_name: Path) -> bool:
        """Check whether the tile is drawn."""
        return self.get_file_name(directory_name).with_suffix(".png").exists()

    def get_carto_address(self) -> str:
        """Get URL of this tile from the OpenStreetMap server."""
        return (
            f"https://tile.openstreetmap.org/{self.scale}/{self.x}/{self.y}.png"
        )

    def draw(
        self,
        directory_name: Path,
        cache_path: Path,
        configuration: MapConfiguration,
    ) -> None:
        """
        Draw tile to SVG and PNG files.

        :param directory_name: output directory to storing tiles
        :param cache_path: directory to store SVG and PNG tiles
        :param configuration: drawing configuration
        """
        try:
            osm_data: OSMData = self.load_osm_data(cache_path)
        except NetworkError as e:
            raise NetworkError(f"Map is not loaded. {e.message}")

        self.draw_with_osm_data(osm_data, directory_name, configuration)

    def draw_with_osm_data(
        self,
        osm_data: OSMData,
        directory_name: Path,
        configuration: MapConfiguration,
    ) -> None:
        """Draw SVG and PNG tile using OpenStreetMap data."""
        top, left = self.get_coordinates()
        bottom, right = Tile(
            self.x + 1, self.y + 1, self.scale
        ).get_coordinates()

        flinger: Flinger = Flinger(
            BoundaryBox(left, bottom, right, top), self.scale
        )
        size: np.ndarray = flinger.size

        output_file_name: Path = self.get_file_name(directory_name)

        svg: svgwrite.Drawing = svgwrite.Drawing(
            str(output_file_name), size=size
        )
        icon_extractor: ShapeExtractor = ShapeExtractor(
            workspace.ICONS_PATH, workspace.ICONS_CONFIG_PATH
        )
        scheme: Scheme = Scheme(workspace.DEFAULT_SCHEME_PATH)
        constructor: Constructor = Constructor(
            osm_data, flinger, scheme, icon_extractor, configuration
        )
        constructor.construct()

        painter: Map = Map(
            flinger=flinger, svg=svg, scheme=scheme, configuration=configuration
        )
        painter.draw(constructor)

        with output_file_name.open("w") as output_file:
            svg.write(output_file)
        logging.info(f"Tile is drawn to {output_file_name}.")

        output_path: Path = output_file_name.with_suffix(".png")
        with output_file_name.open() as input_file:
            cairosvg.svg2png(file_obj=input_file, write_to=str(output_path))
        logging.info(f"SVG file is rasterized to {output_path}.")


@dataclass
class Tiles:
    """
    Collection of tiles.
    """

    tiles: list[Tile]
    tile_1: Tile  # Left top tile.
    tile_2: Tile  # Right bottom tile.
    scale: int  # OpenStreetMap zoom level.
    boundary_box: BoundaryBox

    @classmethod
    def from_boundary_box(
        cls, boundary_box: BoundaryBox, scale: int
    ) -> "Tiles":
        """
        Create minimal set of tiles that covers boundary box.

        :param boundary_box: area to be covered by tiles
        :param scale: OpenStreetMap zoom level
        """
        tiles: list[Tile] = []
        tile_1: Tile = Tile.from_coordinates(boundary_box.get_left_top(), scale)
        tile_2: Tile = Tile.from_coordinates(
            boundary_box.get_right_bottom(), scale
        )
        for x in range(tile_1.x, tile_2.x + 1):
            for y in range(tile_1.y, tile_2.y + 1):
                tiles.append(Tile(x, y, scale))

        latitude_2, longitude_1 = tile_1.get_coordinates()
        latitude_1, longitude_2 = Tile(
            tile_2.x + 1, tile_2.y + 1, scale
        ).get_coordinates()
        assert longitude_2 > longitude_1
        assert latitude_2 > latitude_1

        extended_boundary_box: BoundaryBox = BoundaryBox(
            longitude_1, latitude_1, longitude_2, latitude_2
        ).round()

        return cls(tiles, tile_1, tile_2, scale, extended_boundary_box)

    def load_osm_data(self, cache_path: Path) -> OSMData:
        """Load OpenStreetMap data."""
        cache_file_path: Path = (
            cache_path / f"{self.boundary_box.get_format()}.osm"
        )
        get_osm(self.boundary_box, cache_file_path)

        return OSMReader().parse_osm_file(cache_file_path)

    def draw_separately(
        self, directory: Path, cache_path: Path, configuration: MapConfiguration
    ) -> None:
        """
        Draw set of tiles as SVG file separately and rasterize them into a set
        of PNG files with cairosvg.

        :param directory: directory for tiles
        :param cache_path: directory for temporary OSM files
        :param configuration: drawing configuration
        """
        osm_data: OSMData = self.load_osm_data(cache_path)
        for tile in self.tiles:
            file_path: Path = tile.get_file_name(directory)
            if not file_path.exists():
                tile.draw_with_osm_data(osm_data, directory, configuration)
            else:
                logging.debug(f"File {file_path} already exists.")

            output_path: Path = file_path.with_suffix(".png")
            if not output_path.exists():
                with file_path.open() as input_file:
                    cairosvg.svg2png(
                        file_obj=input_file, write_to=str(output_path)
                    )
                logging.info(f"SVG file is rasterized to {output_path}.")
            else:
                logging.debug(f"File {output_path} already exists.")

    def tiles_exist(self, directory_name: Path) -> bool:
        """Check whether all tiles are drawn."""
        return all(x.exists(directory_name) for x in self.tiles)

    def draw(
        self,
        directory: Path,
        cache_path: Path,
        configuration: MapConfiguration,
        osm_data: OSMData,
    ) -> None:
        """
        Draw one PNG image with all tiles and split it into a set of separate
        PNG file with Pillow.

        :param directory: directory for tiles
        :param cache_path: directory for temporary OSM files
        :param configuration: drawing configuration
        :param osm_data: OpenStreetMap data
        """
        if self.tiles_exist(directory):
            return

        self.draw_image_from_osm_data(cache_path, configuration, osm_data)

        input_path: Path = self.get_file_path(cache_path).with_suffix(".png")
        with input_path.open("rb") as input_file:
            image: Image = Image.open(input_file)

            for tile in self.tiles:
                x: int = tile.x - self.tile_1.x
                y: int = tile.y - self.tile_1.y
                area: tuple[int, int, int, int] = (
                    x * TILE_WIDTH,
                    y * TILE_HEIGHT,
                    (x + 1) * TILE_WIDTH,
                    (y + 1) * TILE_HEIGHT,
                )
                cropped: Image = image.crop(area)
                cropped.crop((0, 0, TILE_WIDTH, TILE_HEIGHT)).save(
                    tile.get_file_name(directory).with_suffix(".png")
                )
                logging.info(f"Tile {tile.scale}/{tile.x}/{tile.y} is created.")

    def get_file_path(self, cache_path: Path) -> Path:
        """Get path of the output SVG file."""
        return cache_path / f"{self.boundary_box.get_format()}_{self.scale}.svg"

    def draw_image(
        self, cache_path: Path, configuration: MapConfiguration
    ) -> None:
        """
        Draw all tiles as one picture.

        :param cache_path: directory for temporary SVG file and OSM files
        :param configuration: drawing configuration
        """
        osm_data: OSMData = self.load_osm_data(cache_path)
        self.draw_image_from_osm_data(cache_path, configuration, osm_data)

    def draw_image_from_osm_data(
        self,
        cache_path: Path,
        configuration: MapConfiguration,
        osm_data: OSMData,
    ) -> None:
        """Draw all tiles using OSM data."""
        output_path: Path = self.get_file_path(cache_path)

        if not output_path.exists():
            top, left = self.tile_1.get_coordinates()
            bottom, right = Tile(
                self.tile_2.x + 1, self.tile_2.y + 1, self.scale
            ).get_coordinates()

            flinger: Flinger = Flinger(
                BoundaryBox(left, bottom, right, top), self.scale
            )
            extractor: ShapeExtractor = ShapeExtractor(
                workspace.ICONS_PATH, workspace.ICONS_CONFIG_PATH
            )
            scheme: Scheme = Scheme(workspace.DEFAULT_SCHEME_PATH)
            constructor: Constructor = Constructor(
                osm_data, flinger, scheme, extractor, configuration
            )
            constructor.construct()

            svg: svgwrite.Drawing = svgwrite.Drawing(
                str(output_path), size=flinger.size
            )
            map_: Map = Map(flinger, svg, scheme, configuration)
            map_.draw(constructor)

            logging.info(f"Writing output SVG {output_path}...")
            with output_path.open("w+") as output_file:
                svg.write(output_file)
        else:
            logging.debug(f"File {output_path} already exists.")

        png_path: Path = self.get_file_path(cache_path).with_suffix(".png")
        if not png_path.exists():
            with output_path.open() as input_file:
                cairosvg.svg2png(file_obj=input_file, write_to=str(png_path))
            logging.info(f"SVG file is rasterized to {png_path}.")
        else:
            logging.debug(f"File {png_path} already exists.")


class ScaleConfigurationException(Exception):
    """Wrong configuration format."""


def parse_scale(scale_specification: str) -> list[int]:
    """Parse scale specification."""
    parts: list[str]
    if "," in scale_specification:
        parts = scale_specification.split(",")
    else:
        parts = [scale_specification]

    def parse(scale: str) -> int:
        """Parse scale."""
        parsed_scale: int = int(scale)
        if parsed_scale <= 0:
            raise ScaleConfigurationException("Non positive scale.")
        if parsed_scale > 20:
            raise ScaleConfigurationException("Scale is too big.")
        return parsed_scale

    result: list[int] = []
    for part in parts:
        if "-" in part:
            from_, to = part.split("-")
            from_scale: int = parse(from_)
            to_scale: int = parse(to)
            if from_scale > to_scale:
                raise ScaleConfigurationException("Wrong range.")
            result += range(from_scale, to_scale + 1)
        else:
            result.append(parse(part))

    return result


def ui(options: argparse.Namespace) -> None:
    """Simple user interface for tile generation."""
    directory: Path = workspace.get_tile_path()
    configuration: MapConfiguration = MapConfiguration.from_options(options)

    scales: list[int] = parse_scale(options.scales)
    min_scale: int = min(scales)

    if options.coordinates:
        coordinates: list[float] = list(
            map(float, options.coordinates.strip().split(","))
        )
        min_tile: Tile = Tile.from_coordinates(np.array(coordinates), min_scale)
        try:
            osm_data: OSMData = min_tile.load_osm_data(Path(options.cache))
        except NetworkError as e:
            raise NetworkError(f"Map is not loaded. {e.message}")

        for scale in scales:
            tile: Tile = Tile.from_coordinates(np.array(coordinates), scale)
            try:
                tile.draw_with_osm_data(osm_data, directory, configuration)
            except NetworkError as e:
                logging.fatal(e.message)
    elif options.tile:
        scale, x, y = map(int, options.tile.split("/"))
        tile: Tile = Tile(x, y, scale)
        tile.draw(directory, Path(options.cache), configuration)
    elif options.boundary_box:
        boundary_box: Optional[BoundaryBox] = BoundaryBox.from_text(
            options.boundary_box
        )
        if boundary_box is None:
            sys.exit(1)
        min_tiles: Tiles = Tiles.from_boundary_box(boundary_box, min_scale)
        extended_boundary_box: BoundaryBox = min_tiles.boundary_box
        try:
            osm_data: OSMData = min_tiles.load_osm_data(Path(options.cache))
        except NetworkError as e:
            raise NetworkError(f"Map is not loaded. {e.message}")

        for scale in scales:
            tiles: Tiles = Tiles.from_boundary_box(extended_boundary_box, scale)
            tiles.draw(directory, Path(options.cache), configuration, osm_data)
    else:
        logging.fatal(
            "Specify either --coordinates, --boundary-box, or --tile."
        )
        sys.exit(1)
