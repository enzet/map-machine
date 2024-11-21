"""Icon grids for documentation."""

from pathlib import Path
from typing import Iterable

from colour import Color

from map_machine.pictogram.icon import (
    Shape,
    Icon,
    ShapeSpecification,
    ShapeExtractor,
)
from map_machine.pictogram.icon_collection import IconCollection
from map_machine.workspace import workspace

SKIP: bool = True


def draw_special_grid(all_shapes, function, path, color=None):
    """Draw special icon grid to illustrate map feature."""
    icons = [
        Icon([ShapeSpecification(shape)])
        for shape in all_shapes
        if function(shape)
    ]
    icons = sorted(icons)

    if color:
        for icon in icons:
            icon.recolor(color)

    IconCollection(icons).draw_grid(path, 8, scale=4.0)


def draw_special_grids():
    """Draw special icon grids."""
    extractor: ShapeExtractor = ShapeExtractor(
        workspace.ICONS_PATH, workspace.ICONS_CONFIG_PATH
    )
    all_shapes: Iterable[Shape] = extractor.shapes.values()

    draw_special_grid(
        all_shapes,
        lambda shape: shape.id_.startswith("power_tower")
        or shape.id_.startswith("power_pole"),
        Path("doc/icons_power.svg"),
    )
    if SKIP:
        draw_special_grid(
            all_shapes,
            lambda shape: shape.group == "root_space",
            Path("doc/icons_space.svg"),
        )
    draw_special_grid(
        all_shapes,
        lambda shape: shape.group == "root_street_playground",
        Path("doc/icons_playground.svg"),
    )
    draw_special_grid(
        all_shapes,
        lambda shape: "emergency" in shape.categories,
        Path("doc/icons_emergency.svg"),
        color=Color("#DD2222"),
    )
    draw_special_grid(
        all_shapes,
        lambda shape: shape.id_.startswith("japan"),
        Path("doc/icons_japanese.svg"),
    )


if __name__ == "__main__":
    draw_special_grids()
