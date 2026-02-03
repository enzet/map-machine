"""Map drawing configuration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from colour import Color

if TYPE_CHECKING:
    import argparse

    from map_machine.pictogram.icon import IconSet
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


class RoadMode(Enum):
    """Road drawing mode."""

    """Don't draw any kinds of roads."""
    NO = "no"

    """Draw roads as other styled lines."""
    SIMPLE = "simple"

    """Draw roads trying to display their actual width and lanes number."""
    LANES = "lanes"


@dataclass
class MapConfiguration:
    """Map drawing configuration."""

    scheme: Scheme
    drawing_mode: DrawingMode = DrawingMode.NORMAL
    building_mode: BuildingMode = BuildingMode.FLAT
    road_mode: RoadMode = RoadMode.LANES
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
    credit: str | None = "© OpenStreetMap contributors"
    show_credit: bool = True
    draw_background: bool = True
    crop_ways: bool = True
    crop_margin: float = 25.0

    @classmethod
    def from_options(
        cls, scheme: Scheme, options: argparse.Namespace, zoom_level: float
    ) -> MapConfiguration:
        """Initialize from command-line options.

        Scheme YAML values are the defaults.  CLI options override them
        when explicitly provided (i.e. not `None`).
        """

        def _resolve(
            cli_value: Any,  # noqa: ANN401
            scheme_value: Any,  # noqa: ANN401
            enum_cls: type[Enum] | None = None,
        ) -> Any:  # noqa: ANN401
            if cli_value is None:
                return scheme_value
            if enum_cls is not None:
                return enum_cls(cli_value)
            return cli_value

        return cls(
            scheme,
            _resolve(options.mode, scheme.drawing_mode, DrawingMode),
            _resolve(options.buildings, scheme.building_mode, BuildingMode),
            _resolve(options.roads, scheme.road_mode, RoadMode),
            _resolve(options.label_mode, scheme.label_mode, LabelMode),
            zoom_level,
            options.overlap,
            options.level,
            options.seed,
            options.tooltips,
            options.country,
            options.ignore_level_matching,
            _resolve(options.roofs, scheme.roofs),
            _resolve(options.building_colors, scheme.building_colors),
            options.show_overlapped,
            show_credit=not options.hide_credit,
            draw_background=_resolve(options.background, scheme.background),
            crop_ways=options.crop,
            crop_margin=options.crop_margin,
        )

    def is_wireframe(self) -> bool:
        """Whether drawing mode is special."""
        return self.drawing_mode != DrawingMode.NORMAL

    def background_color(self) -> Color | None:
        """Get background map color based on drawing mode."""
        if self.drawing_mode not in (DrawingMode.NORMAL, DrawingMode.BLACK):
            return DARK_BACKGROUND
        return None

    def get_icon(
        self,
        tags: dict[str, Any],
        processed: set[str],
    ) -> tuple[IconSet | None, int]:
        """Get icon set.

        :return: (icon set, priority)
        """
        return self.scheme.get_icon(
            tags,
            processed,
            self.country,
            self.zoom_level,
            ignore_level_matching=self.ignore_level_matching,
            show_overlapped=self.show_overlapped,
        )
