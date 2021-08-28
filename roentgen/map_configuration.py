"""
Map drawing configuration.
"""
import argparse
from dataclasses import dataclass
from enum import Enum

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


class DrawingMode(Enum):
    """
    Map drawing mode.
    """

    NORMAL: str = "normal"
    AUTHOR: str = "author"
    TIME: str = "time"


class LabelMode(Enum):
    """
    Label drawing mode.
    """

    NO: str = "no"
    MAIN: str = "main"
    ALL: str = "all"


class BuildingMode(Enum):
    """
    Building drawing mode.
    """

    FLAT: str = "flat"
    ISOMETRIC: str = "isometric"
    ISOMETRIC_NO_PARTS: str = "isometric-no-parts"


@dataclass
class MapConfiguration:
    """
    Map drawing configuration.
    """

    drawing_mode: DrawingMode = DrawingMode.NORMAL
    building_mode: BuildingMode = BuildingMode.FLAT
    label_mode: LabelMode = LabelMode.MAIN
    zoom_level: int = 18
    overlap: int = 12
    level: str = "overground"
    seed: str = ""

    @classmethod
    def from_options(cls, options: argparse.Namespace) -> "MapConfiguration":
        """Initialize from command-line options."""
        return cls(
            DrawingMode(options.mode),
            BuildingMode(options.buildings),
            LabelMode(options.label_mode),
            options.zoom,
            options.overlap,
            options.level,
            options.seed,
        )

    def is_wireframe(self) -> bool:
        """Whether drawing mode is special."""
        return self.drawing_mode != DrawingMode.NORMAL
