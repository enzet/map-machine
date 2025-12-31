"""Icon grid drawing."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from colour import Color
from roentgen import Roentgen, get_roentgen
from roentgen.icon import IconSpecification, ShapeSpecification
from svgwrite import Drawing

from map_machine.scheme import Scheme
from map_machine.workspace import workspace

if TYPE_CHECKING:
    from pathlib import Path

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

logger: logging.Logger = logging.getLogger(__name__)

roentgen: Roentgen = get_roentgen()

WHITE: Color = Color("white")
BLACK: Color = Color("black")


@dataclass
class IconCollection:
    """Collection of icons."""

    icon_specifications: list[IconSpecification]

    @classmethod
    def from_scheme(
        cls,
        scheme: Scheme,
        background_color: Color = WHITE,
        color: Color = BLACK,
        *,
        add_unused: bool = False,
        add_all: bool = False,
    ) -> IconCollection:
        """Collect all possible icon combinations.

        This collection won't contain icons for tags matched with regular
        expressions. E.g. traffic_sign=maxspeed; maxspeed=42.

        :param scheme: tag specification
        :param extractor: shape extractor for icon creation
        :param background_color: background color
        :param color: icon color
        :param add_unused: create icons from shapes that have no corresponding
            tags
        :param add_all: create icons from all possible shapes including parts
        """
        icon_specifications: list[IconSpecification] = []

        def add(current_set: list[dict[str, str]]) -> None:
            """Construct icon and add it to the list."""
            specifications: list[ShapeSpecification] = []
            for shape_specification in current_set:
                if "#" in shape_specification["shape"]:
                    return
                specifications.append(
                    scheme.get_shape_specification(shape_specification)
                )
            constructed_icon_specification: IconSpecification = (
                IconSpecification("", specifications, "")
            )
            constructed_icon_specification.recolor(
                color, white=background_color
            )
            if constructed_icon_specification not in icon_specifications:
                icon_specifications.append(constructed_icon_specification)

        for matcher in scheme.node_matchers:
            if matcher.shapes:
                add(matcher.shapes)
            if matcher.add_shapes:
                add(matcher.add_shapes)
            if not matcher.over_icon:
                continue
            if matcher.under_icon:
                for icon_id in matcher.under_icon:
                    add([icon_id, *matcher.over_icon])
            if not (matcher.under_icon and matcher.with_icon):
                continue
            for icon_id in matcher.under_icon:
                for icon_2_id in matcher.with_icon:
                    add([icon_id, icon_2_id, *matcher.over_icon])
                for icon_2_id in matcher.with_icon:
                    for icon_3_id in matcher.with_icon:
                        if (
                            icon_2_id not in (icon_3_id, icon_id)
                            and icon_3_id != icon_id
                        ):
                            add(
                                [
                                    icon_id,
                                    icon_2_id,
                                    icon_3_id,
                                    *matcher.over_icon,
                                ]
                            )

        specified_ids: set[str] = set()

        for icon_specification in icon_specifications:
            specified_ids |= set(icon_specification.get_shape_ids())

        all_ids: list[str] = roentgen.get_ids()

        if add_unused:
            for shape_id in set(all_ids) - specified_ids:
                icon_specification = IconSpecification(
                    "", [ShapeSpecification(shape_id)], ""
                )
                icon_specification.recolor(color, white=background_color)
                icon_specifications.append(icon_specification)

        if add_all:
            for shape_id in all_ids:
                icon_specification = IconSpecification(
                    "", [ShapeSpecification(shape_id)], ""
                )
                icon_specification.recolor(color, white=background_color)
                icon_specifications.append(icon_specification)

        return cls(icon_specifications)

    def draw_icons(
        self,
        output_directory: Path,
        license_text: str,
        *,
        color: Color | None = None,
        outline: bool = False,
        outline_opacity: float = 1.0,
    ) -> None:
        """Draw individual icons.

        :param output_directory: path to the directory to store individual SVG
            files for icons
        :param license: license text
        :param by_name: use names instead of identifiers
        :param color: fill color
        :param outline: if true, draw outline beneath the icon
        :param outline_opacity: opacity of the outline
        """
        for icon_specification in self.icon_specifications:
            icon_specification.draw_to_file(
                output_directory
                / f"{'___'.join(icon_specification.get_shape_ids())}.svg",
                roentgen.get_shapes(),
                color=color,
                outline=outline,
                outline_opacity=outline_opacity,
            )

        with (output_directory / "LICENSE").open(
            "w", encoding="utf-8"
        ) as output_file:
            output_file.write(license_text)

    def draw_grid(
        self,
        file_name: Path,
        columns: int = 16,
        step: float = 24.0,
        background_color: Color | None = WHITE,
        scale: float = 1.0,
    ) -> None:
        """Draw icons in the form of table.

        :param file_name: output SVG file name
        :param columns: number of columns in grid
        :param step: horizontal and vertical distance between icons in grid
        :param background_color: background color
        :param scale: scale icon by the magnitude
        """
        point: tuple[float, float] = (step / 2.0 * scale, step / 2.0 * scale)
        width: float = step * columns * scale

        height: int = int(
            int(len(self.icon_specifications) / columns + 1.0) * step * scale
        )
        svg: Drawing = Drawing(str(file_name), (width, height))
        if background_color is not None:
            svg.add(
                svg.rect((0, 0), (width, height), fill=background_color.hex)
            )

        for icon_specification in self.icon_specifications:
            icon_specification.draw(
                svg, roentgen.get_shapes(), point, scale=scale
            )
            point += np.array((step * scale, 0.0))
            if point[0] > width - 8.0:
                point[0] = step / 2.0 * scale
                point += np.array((0.0, step * scale))
                height += int(step * scale)

        with file_name.open("w", encoding="utf-8") as output_file:
            svg.write(output_file)

    def __len__(self) -> int:
        return len(self.icon_specifications)

    def sort(self) -> None:
        """Sort icon list."""
        self.icon_specifications = sorted(self.icon_specifications)


def draw_icons() -> None:
    """Draw all possible icon shapes combinations.

    This includes drawing icons as grid in one SVG file and as individual SVG
    files.
    """
    scheme: Scheme = Scheme.from_file(workspace.DEFAULT_SCHEME_PATH)
    collection: IconCollection = IconCollection.from_scheme(scheme)
    collection.sort()

    # Draw individual icons.

    icons_by_id_path: Path = workspace.get_icons_by_id_path()
    collection.draw_icons(icons_by_id_path, roentgen.get_license())

    logger.info("Icons are written to `%s`.", icons_by_id_path)

    # Draw grid.

    for icon in collection.icon_specifications:
        icon.recolor(Color("#444444"))

    for path, scale in (
        (workspace.get_icon_grid_path(), 1.0),
        (workspace.GRID_PATH, 2.0),
    ):
        collection.draw_grid(path, scale=scale)
        logger.info("Icon grid is written to `%s`.", path)
