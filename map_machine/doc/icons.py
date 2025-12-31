"""Icon grids for documentation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from colour import Color
from roentgen import Roentgen, get_roentgen
from roentgen.icon import IconSpecification, Shape, ShapeSpecification

from map_machine.pictogram.icon_collection import IconCollection

if TYPE_CHECKING:
    from collections.abc import Callable

SKIP: bool = True
BLACK: Color = Color("black")


roentgen: Roentgen = get_roentgen()


def draw_special_grid(
    all_shapes: dict[str, Shape],
    function: Callable[[Shape], bool],
    path: Path,
    color: Color | None = None,
) -> None:
    """Draw special icon grid to illustrate map feature."""
    icons: list[IconSpecification] = [
        IconSpecification("", [ShapeSpecification(shape_id)], "")
        for shape_id, shape in all_shapes.items()
        if function(shape)
    ]
    icons.sort()

    if color:
        for icon in icons:
            icon.recolor(color)

    IconCollection(icons).draw_grid(path, 8, scale=4.0)


def draw_special_grids() -> None:
    """Draw special icon grids."""
    all_shapes: dict[str, Shape] = roentgen.get_shapes().shapes

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
