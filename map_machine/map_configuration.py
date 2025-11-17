"""Map drawing configuration."""
import argparse
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any

from colour import Color

from map_machine.pictogram.icon import ShapeExtractor, IconSet
from map_machine.scheme import Scheme

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

DARK_BACKGROUND: Color = Color("#111111")


class DrawingMode(Enum):
    """Map drawing mode."""

    NORMAL = "normal"
    AUTHOR = "author"
    TIME = "time"
    WHITE = "white"
    BLACK = "black"


class LabelMode(Enum):
    """Label drawing mode."""

    NO = "no"
    MAIN = "main"
    ALL = "all"
    ADDRESS = "address"


class BuildingMode(Enum):
    """Building drawing mode."""

    NO = "no"
    FLAT = "flat"
    ISOMETRIC = "isometric"
    ISOMETRIC_NO_PARTS = "isometric-no-parts"


@dataclass
class MapConfiguration:
    """Map drawing configuration."""

    scheme: Scheme
    drawing_mode: DrawingMode = DrawingMode.NORMAL
    building_mode: BuildingMode = BuildingMode.FLAT
    label_mode: LabelMode = LabelMode.MAIN
    zoom_level: float = 18.0
    overlap: int = 12
    level: str = "overground"
    seed: str = ""
    show_tooltips: bool = False
    country: str = "world"
    ignore_level_matching: bool = False
    draw_roofs: bool = True
    use_building_colors: bool = False
    show_overlapped: bool = False
    credit: Optional[str] = "© OpenStreetMap contributors"
    show_credit: bool = True
    draw_background: bool = True

    @classmethod
    def from_options(
        cls, scheme: Scheme, options: argparse.Namespace, zoom_level: float
    ) -> "MapConfiguration":
        """Initialize from command-line options."""
        return cls(
            scheme,
            DrawingMode(options.mode),
            BuildingMode(options.buildings),
            LabelMode(options.label_mode),
            zoom_level,
            options.overlap,
            options.level,
            options.seed,
            options.tooltips,
            options.country,
            options.ignore_level_matching,
            options.roofs,
            options.building_colors,
            options.show_overlapped,
            show_credit=not options.hide_credit,
            draw_background=options.background,
        )

    def is_wireframe(self) -> bool:
        """Whether drawing mode is special."""
        return self.drawing_mode != DrawingMode.NORMAL

    def background_color(self) -> Optional[Color]:
        """Get background map color based on drawing mode."""
        if self.drawing_mode not in (DrawingMode.NORMAL, DrawingMode.BLACK):
            return DARK_BACKGROUND
        return None

    def get_icon(
        self,
        extractor: ShapeExtractor,
        tags: dict[str, Any],
        processed: set[str],
    ) -> tuple[Optional[IconSet], int]:
        return self.scheme.get_icon(
            extractor,
            tags,
            processed,
            self.country,
            self.zoom_level,
            self.ignore_level_matching,
            self.show_overlapped,
        )
