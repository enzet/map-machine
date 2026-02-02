"""Tile generation.

See https://wiki.openstreetmap.org/wiki/Tiles
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import cairosvg
import numpy as np
import svgwrite
from PIL import Image

from map_machine.constructor import Constructor
from map_machine.geometry.bounding_box import BoundingBox
from map_machine.geometry.flinger import MercatorFlinger
from map_machine.map_configuration import MapConfiguration
from map_machine.mapper import Map
from map_machine.osm.osm_getter import (
    NetworkError,
    find_incomplete_relations,
    get_osm,
    get_overpass_relations,
)
from map_machine.osm.osm_reader import OSMData
from map_machine.scheme import Scheme
from map_machine.workspace import workspace

if TYPE_CHECKING:
    import argparse

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

logger: logging.Logger = logging.getLogger(__name__)

TILE_WIDTH, TILE_HEIGHT = 256, 256
EXTEND_TO_BIGGER_TILE: bool = False
MAX_ZOOM_LEVEL: int = 20


def complete_relations(osm_data: OSMData, cache_path: Path) -> None:
    """Download missing relation member data via Overpass API.

    :param osm_data: parsed OSM data (modified in place)
    :param cache_path: directory for caching Overpass responses
    """
    incomplete_ids: list[int] = find_incomplete_relations(osm_data)
    if not incomplete_ids:
        return

    logger.info(
        "Found %d incomplete relations, fetching via Overpass API...",
        len(incomplete_ids),
    )
    overpass_data: bytes | None = get_overpass_relations(
        incomplete_ids, cache_path
    )
    if overpass_data:
        osm_data.merge_overpass_response(overpass_data.decode("utf-8"))
        logger.info(
            "Merged Overpass data for %d relations.", len(incomplete_ids)
        )
    else:
        logger.warning("Failed to fetch Overpass data, using partial data.")


@dataclass
class Tile:
    """OpenStreetMap tile.

    Square bitmap graphics displayed in a grid arrangement to show a map.
    """

    x: int
    y: int
    zoom_level: int

    @classmethod
    def from_coordinates(cls, coordinates: np.ndarray, zoom_level: int) -> Tile:
        """Code from https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames.

        :param coordinates: any coordinates inside tile, (latitude, longitude)
        :param zoom_level: zoom level in OpenStreetMap terminology
        """
        lat_rad: np.ndarray = np.radians(coordinates[0])
        scale: float = 2.0**zoom_level
        x: int = int((coordinates[1] + 180.0) / 360.0 * scale)
        y: int = int((1.0 - np.arcsinh(np.tan(lat_rad)) / np.pi) / 2.0 * scale)
        return cls(x, y, zoom_level)

    def get_coordinates(self) -> np.ndarray:
        """Return geo coordinates of the north-west corner of the tile.

        Code is from https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames.
        """
        scale: float = 2.0**self.zoom_level
        longitude_degree: float = self.x / scale * 360.0 - 180.0
        latitude_radians: float = np.arctan(
            np.sinh(np.pi * (1 - 2 * self.y / scale))
        )
        latitude_degree: np.ndarray = np.degrees(latitude_radians)
        return np.array((latitude_degree, longitude_degree))

    def get_bounding_box(self) -> BoundingBox:
        """Get geographical bounding box of the tile.

        North-west and south-east points.
        """
        point_1: np.ndarray = self.get_coordinates()
        point_2: np.ndarray = Tile(
            self.x + 1, self.y + 1, self.zoom_level
        ).get_coordinates()

        return BoundingBox(
            float(point_1[1]),
            float(point_2[0]),
            float(point_2[1]),
            float(point_1[0]),
        )

    def get_extended_bounding_box(self) -> BoundingBox:
        """Get extended geographical bounding box of the tile.

        North-west and south-east points.
        """
        point_1: np.ndarray = self.get_coordinates()
        point_2: np.ndarray = Tile(
            self.x + 1, self.y + 1, self.zoom_level
        ).get_coordinates()

        return BoundingBox(
            float(point_1[1]),
            float(point_2[0]),
            float(point_2[1]),
            float(point_1[0]),
        ).round()

    def load_osm_data(self, cache_path: Path) -> OSMData:
        """Construct map data from extended bounding box.

        :param cache_path: directory to store OSM data files
        """
        cache_file_path: Path = (
            cache_path / f"{self.get_extended_bounding_box().get_format()}.osm"
        )
        get_osm(self.get_extended_bounding_box(), cache_file_path)

        osm_data: OSMData = OSMData()
        osm_data.parse_osm_file(cache_file_path)

        return osm_data

    def get_file_name(self, directory_name: Path) -> Path:
        """Get tile output SVG file path."""
        return directory_name / f"tile_{self.zoom_level}_{self.x}_{self.y}.svg"

    def exists(self, directory_name: Path) -> bool:
        """Check whether the tile is drawn."""
        return self.get_file_name(directory_name).with_suffix(".png").exists()

    def get_carto_address(self) -> str:
        """Get URL of this tile from the OpenStreetMap server."""
        return (
            f"https://tile.openstreetmap.org/"
            f"{self.zoom_level}/{self.x}/{self.y}.png"
        )

    def draw(
        self,
        directory_name: Path,
        cache_path: Path,
        configuration: MapConfiguration,
        *,
        use_overpass: bool = True,
    ) -> None:
        """Draw tile to SVG and PNG files.

        :param directory_name: output directory for storing tiles
        :param cache_path: directory to store SVG and PNG tiles
        :param configuration: drawing configuration
        :param use_overpass: fetch missing relation data via Overpass API
        """
        try:
            osm_data: OSMData = self.load_osm_data(cache_path)
        except NetworkError as error:
            msg = f"Map is not loaded. {error.message}"
            raise NetworkError(msg) from error

        if use_overpass:
            complete_relations(osm_data, cache_path)

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
            self.x + 1, self.y + 1, self.zoom_level
        ).get_coordinates()

        bounding_box: BoundingBox = BoundingBox(left, bottom, right, top)
        flinger: MercatorFlinger = MercatorFlinger(
            bounding_box,
            self.zoom_level,
            osm_data.equator_length,
        )
        size: np.ndarray = flinger.size

        output_file_name: Path = self.get_file_name(directory_name)

        svg: svgwrite.Drawing = svgwrite.Drawing(
            str(output_file_name), size=size
        )
        constructor: Constructor = Constructor(
            osm_data, flinger, configuration, bounding_box=bounding_box
        )
        constructor.construct()

        painter: Map = Map(
            flinger=flinger, svg=svg, configuration=configuration
        )
        painter.draw(constructor)

        with output_file_name.open("w", encoding="utf-8") as output_file:
            svg.write(output_file)
        logger.info("Tile is drawn to `%s`.", output_file_name)

        output_path: Path = output_file_name.with_suffix(".png")
        with output_file_name.open(encoding="utf-8") as input_file:
            cairosvg.svg2png(file_obj=input_file, write_to=str(output_path))
        logger.info("SVG file is rasterized to `%s`.", output_path)

    def subdivide(self, zoom_level: int) -> list[Tile]:
        """Get subtiles of the tile."""
        assert zoom_level >= self.zoom_level

        tiles: list[Tile] = []
        scale: int = 2 ** (zoom_level - self.zoom_level)
        for i in range(scale):
            for j in range(scale):
                tile: Tile = Tile(
                    scale * self.x + i, scale * self.y + j, zoom_level
                )
                tiles.append(tile)
        return tiles


@dataclass
class Tiles:
    """Collection of tiles."""

    tiles: list[Tile]
    tile_1: Tile  # Left top tile.
    tile_2: Tile  # Right bottom tile.
    zoom_level: int  # OpenStreetMap zoom level.
    bounding_box: BoundingBox

    @classmethod
    def from_bounding_box(
        cls, bounding_box: BoundingBox, zoom_level: int
    ) -> Tiles:
        """Create minimal set of tiles that covers bounding box.

        :param bounding_box: area to be covered by tiles
        :param zoom_level: zoom level in OpenStreetMap terminology
        """
        tile_1: Tile = Tile.from_coordinates(
            bounding_box.get_left_top(), zoom_level
        )
        tile_2: Tile = Tile.from_coordinates(
            bounding_box.get_right_bottom(), zoom_level
        )
        tiles: list[Tile] = [
            Tile(x, y, zoom_level)
            for x in range(tile_1.x, tile_2.x + 1)
            for y in range(tile_1.y, tile_2.y + 1)
        ]

        latitude_2, longitude_1 = tile_1.get_coordinates()
        latitude_1, longitude_2 = Tile(
            tile_2.x + 1, tile_2.y + 1, zoom_level
        ).get_coordinates()
        assert longitude_2 > longitude_1
        assert latitude_2 > latitude_1

        extended_bounding_box: BoundingBox = BoundingBox(
            longitude_1, latitude_1, longitude_2, latitude_2
        ).round()

        return cls(tiles, tile_1, tile_2, zoom_level, extended_bounding_box)

    def load_osm_data(self, cache_path: Path) -> OSMData:
        """Load OpenStreetMap data."""
        cache_file_path: Path = (
            cache_path / f"{self.bounding_box.get_format()}.osm"
        )
        get_osm(self.bounding_box, cache_file_path)

        osm_data: OSMData = OSMData()
        osm_data.parse_osm_file(cache_file_path)

        return osm_data

    def tiles_exist(self, directory_name: Path) -> bool:
        """Check whether all tiles are drawn."""
        return all(x.exists(directory_name) for x in self.tiles)

    def draw(
        self,
        directory: Path,
        cache_path: Path,
        configuration: MapConfiguration,
        osm_data: OSMData,
        *,
        redraw: bool = False,
    ) -> None:
        """Draw PNG images.

        Draw one PNG image with all tiles and split it into a set of separate
        PNG files with Pillow.

        :param directory: directory for tiles
        :param cache_path: directory for temporary OSM files
        :param configuration: drawing configuration
        :param osm_data: OpenStreetMap data
        :param redraw: update cache
        """
        if self.tiles_exist(directory) and not redraw:
            return

        self.draw_image_from_osm_data(
            cache_path, configuration, osm_data, redraw=redraw
        )
        input_path: Path = self.get_file_path(cache_path).with_suffix(".png")

        with input_path.open("rb") as input_file:
            image: Image.Image = Image.open(input_file)

            for tile in self.tiles:
                x: int = tile.x - self.tile_1.x
                y: int = tile.y - self.tile_1.y
                area: tuple[int, int, int, int] = (
                    x * TILE_WIDTH,
                    y * TILE_HEIGHT,
                    (x + 1) * TILE_WIDTH,
                    (y + 1) * TILE_HEIGHT,
                )
                cropped: Image.Image = image.crop(area)
                cropped.crop((0, 0, TILE_WIDTH, TILE_HEIGHT)).save(
                    tile.get_file_name(directory).with_suffix(".png")
                )
                logger.info(
                    "Tile `%s/%s/%s` is created.",
                    tile.zoom_level,
                    tile.x,
                    tile.y,
                )

    def get_file_path(self, cache_path: Path) -> Path:
        """Get path of the output SVG file."""
        return (
            cache_path
            / f"{self.bounding_box.get_format()}_{self.zoom_level}.svg"
        )

    def draw_image(
        self, cache_path: Path, configuration: MapConfiguration
    ) -> None:
        """Draw all tiles as one picture.

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
        *,
        redraw: bool = False,
    ) -> None:
        """Draw all tiles using OSM data."""
        output_path: Path = self.get_file_path(cache_path)

        if not output_path.exists() or redraw:
            top, left = self.tile_1.get_coordinates()
            bottom, right = Tile(
                self.tile_2.x + 1,
                self.tile_2.y + 1,
                self.zoom_level,
            ).get_coordinates()

            bounding_box: BoundingBox = BoundingBox(left, bottom, right, top)
            flinger: MercatorFlinger = MercatorFlinger(
                bounding_box,
                self.zoom_level,
                osm_data.equator_length,
            )
            constructor: Constructor = Constructor(
                osm_data, flinger, configuration, bounding_box=bounding_box
            )
            constructor.construct()

            svg: svgwrite.Drawing = svgwrite.Drawing(
                str(output_path), size=flinger.size
            )
            map_: Map = Map(flinger, svg, configuration)
            map_.draw(constructor)

            logger.info("Writing output SVG to `%s`...", output_path)
            with output_path.open("w+", encoding="utf-8") as output_file:
                svg.write(output_file)
        else:
            logger.debug("File `%s` already exists.", output_path)

        png_path: Path = self.get_file_path(cache_path).with_suffix(".png")

        if not png_path.exists() or redraw:
            with output_path.open(encoding="utf-8") as input_file:
                cairosvg.svg2png(file_obj=input_file, write_to=str(png_path))
            logger.info("SVG file is rasterized to `%s`.", png_path)
        else:
            logger.debug("File `%s` already exists.", png_path)

    def subdivide(self, zoom_level: int) -> Tiles:
        """Get subtiles from tiles."""
        tiles: list[Tile] = []
        for tile in self.tiles:
            tiles += tile.subdivide(zoom_level)
        return Tiles(
            tiles,
            tiles[0],
            tiles[-1],
            zoom_level,
            self.bounding_box,
        )


class ScaleConfigurationError(Exception):
    """Wrong configuration format."""


def parse_zoom_level(zoom_level_specification: str) -> list[int]:
    """Parse zoom level specification."""
    parts: list[str]
    if "," in zoom_level_specification:
        parts = zoom_level_specification.split(",")
    else:
        parts = [zoom_level_specification]

    def parse(zoom_level: str) -> int:
        """Parse zoom level."""
        parsed_zoom_level: int = int(zoom_level)
        if parsed_zoom_level > MAX_ZOOM_LEVEL:
            message: str = "Scale is too big."
            raise ScaleConfigurationError(message)
        return parsed_zoom_level

    result: list[int] = []
    for part in parts:
        if "-" in part:
            start, end = part.split("-")
            from_zoom_level: int = parse(start)
            to_zoom_level: int = parse(end)
            if from_zoom_level > to_zoom_level:
                message: str = "Wrong range."
                raise ScaleConfigurationError(message)
            result += range(from_zoom_level, to_zoom_level + 1)
        else:
            result.append(parse(part))

    return result


def generate_tiles(options: argparse.Namespace) -> None:
    """Generate tiles through simple user interface."""
    directory: Path = workspace.get_tile_path()

    zoom_levels: list[int] = parse_zoom_level(options.zoom)
    min_zoom_level: int = min(zoom_levels)

    scheme_path: Path | None = workspace.find_scheme_path(options.scheme)
    if not scheme_path:
        logger.fatal("Scheme `%s` not found.", options.scheme)
        return

    scheme: Scheme = Scheme.from_file(scheme_path)
    cache_path: Path = Path(options.cache)
    message: str

    if not cache_path.exists():
        message = (
            f"Cache directory `{cache_path}` does not exist, please create it."
        )
        logger.fatal(message)
        sys.exit(1)

    bounding_box: BoundingBox
    configuration: MapConfiguration
    tile: Tile
    tiles: Tiles
    osm_data: OSMData

    use_overpass: bool = not getattr(options, "no_overpass", False)

    if options.input_file_name:
        osm_data = OSMData()
        osm_data.parse_osm_file(Path(options.input_file_name))

        if use_overpass:
            complete_relations(osm_data, cache_path)

        if osm_data.view_box is None:
            logger.fatal(
                "Failed to parse bounding box input file "
                f"{options.input_file_name}."
            )
            sys.exit(1)
        else:
            bounding_box = osm_data.view_box

        for zoom_level in zoom_levels:
            configuration = MapConfiguration.from_options(
                scheme, options, zoom_level
            )
            tiles = Tiles.from_bounding_box(bounding_box, zoom_level)
            tiles.draw(directory, cache_path, configuration, osm_data)

    elif options.coordinates:
        coordinates: list[float] = list(
            map(float, options.coordinates.strip().split(","))
        )
        min_tile: Tile = Tile.from_coordinates(
            np.array(coordinates), min_zoom_level
        )
        try:
            osm_data = min_tile.load_osm_data(cache_path)
        except NetworkError as error:
            message = f"Map is not loaded. {error.message}"
            raise NetworkError(message) from error

        if use_overpass:
            complete_relations(osm_data, cache_path)

        for zoom_level in zoom_levels:
            tile = Tile.from_coordinates(np.array(coordinates), zoom_level)
            try:
                configuration = MapConfiguration.from_options(
                    scheme, options, zoom_level
                )
                tile.draw_with_osm_data(osm_data, directory, configuration)
            except NetworkError as error:
                logger.fatal(error.message)

    elif options.tile:
        zoom_level, x, y = map(int, options.tile.split("/"))
        tile = Tile(x, y, zoom_level)
        configuration = MapConfiguration.from_options(
            scheme, options, zoom_level
        )
        tile.draw(
            directory,
            cache_path,
            configuration,
            use_overpass=use_overpass,
        )

    elif options.bounding_box:
        try:
            bounding_box = BoundingBox.from_text(options.bounding_box)
        except ValueError:
            message = "Failed to parse bounding box."
            logger.fatal(message)
            sys.exit(1)

        min_tiles: Tiles = Tiles.from_bounding_box(bounding_box, min_zoom_level)
        try:
            osm_data = min_tiles.load_osm_data(cache_path)
        except NetworkError as error:
            message = f"Map is not loaded. {error.message}"
            raise NetworkError(message) from error

        if use_overpass:
            complete_relations(osm_data, cache_path)

        for zoom_level in zoom_levels:
            if EXTEND_TO_BIGGER_TILE:
                tiles = min_tiles.subdivide(zoom_level)
            else:
                tiles = Tiles.from_bounding_box(bounding_box, zoom_level)
            configuration = MapConfiguration.from_options(
                scheme, options, zoom_level
            )
            tiles.draw(directory, cache_path, configuration, osm_data)

    else:
        logger.fatal(
            "Specify either `--coordinates`, `--bounding-box`, `--tile`, or "
            "`--input`."
        )
        sys.exit(1)
