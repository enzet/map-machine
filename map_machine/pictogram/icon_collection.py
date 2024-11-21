"""Icon grid drawing."""

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from colour import Color
from svgwrite import Drawing

from map_machine.pictogram.icon import (
    Icon,
    Shape,
    ShapeExtractor,
    ShapeSpecification,
)
from map_machine.scheme import NodeMatcher, Scheme
from map_machine.workspace import workspace

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


@dataclass
class IconCollection:
    """Collection of icons."""

    icons: list[Icon]

    @classmethod
    def from_scheme(
        cls,
        scheme: Scheme,
        extractor: ShapeExtractor,
        background_color: Color = Color("white"),
        color: Color = Color("black"),
        add_unused: bool = False,
        add_all: bool = False,
    ) -> "IconCollection":
        """
        Collect all possible icon combinations.

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
        icons: list[Icon] = []

        def add(current_set: list[dict[str, str]]) -> None:
            """Construct icon and add it to the list."""
            specifications: list[ShapeSpecification] = []
            for shape_specification in current_set:
                if "#" in shape_specification["shape"]:
                    return
                specifications.append(
                    scheme.get_shape_specification(
                        shape_specification, extractor
                    )
                )
            constructed_icon: Icon = Icon(specifications)
            constructed_icon.recolor(color, white=background_color)
            if constructed_icon not in icons:
                icons.append(constructed_icon)

        for matcher in scheme.node_matchers:
            matcher: NodeMatcher
            if matcher.shapes:
                add(matcher.shapes)
            if matcher.add_shapes:
                add(matcher.add_shapes)
            if not matcher.over_icon:
                continue
            if matcher.under_icon:
                for icon_id in matcher.under_icon:
                    add([icon_id] + matcher.over_icon)
            if not (matcher.under_icon and matcher.with_icon):
                continue
            for icon_id in matcher.under_icon:
                for icon_2_id in matcher.with_icon:
                    add([icon_id] + [icon_2_id] + matcher.over_icon)
                for icon_2_id in matcher.with_icon:
                    for icon_3_id in matcher.with_icon:
                        if (
                            icon_2_id != icon_3_id
                            and icon_2_id != icon_id
                            and icon_3_id != icon_id
                        ):
                            add(
                                [icon_id]
                                + [icon_2_id]
                                + [icon_3_id]
                                + matcher.over_icon
                            )

        specified_ids: set[str] = set()

        for icon in icons:
            specified_ids |= set(icon.get_shape_ids())

        if add_unused:
            for shape_id in extractor.shapes.keys() - specified_ids:
                shape: Shape = extractor.get_shape(shape_id)
                if shape.is_part:
                    continue
                icon: Icon = Icon([ShapeSpecification(shape, color)])
                icon.recolor(color, white=background_color)
                icons.append(icon)

        if add_all:
            for shape_id in extractor.shapes.keys():
                shape: Shape = extractor.get_shape(shape_id)
                icon: Icon = Icon([ShapeSpecification(shape, color)])
                icon.recolor(color, white=background_color)
                icons.append(icon)

        return cls(icons)

    def draw_icons(
        self,
        output_directory: Path,
        license_path: Path,
        by_name: bool = False,
        color: Optional[Color] = None,
        outline: bool = False,
        outline_opacity: float = 1.0,
    ) -> None:
        """
        :param output_directory: path to the directory to store individual SVG
            files for icons
        :param license_path: path to the file with license
        :param by_name: use names instead of identifiers
        :param color: fill color
        :param outline: if true, draw outline beneath the icon
        :param outline_opacity: opacity of the outline
        """
        if by_name:

            def get_file_name(x: Icon) -> str:
                """Generate human-readable file name."""
                return f"Röntgen {x.get_name()}.svg"

        else:

            def get_file_name(x: Icon) -> str:
                """Generate file name with unique identifier."""
                return f"{'___'.join(x.get_shape_ids())}.svg"

        for icon in self.icons:
            icon.draw_to_file(
                output_directory / get_file_name(icon),
                color=color,
                outline=outline,
                outline_opacity=outline_opacity,
            )

        shutil.copy(license_path, output_directory / "LICENSE")

    def draw_grid(
        self,
        file_name: Path,
        columns: int = 16,
        step: float = 24.0,
        background_color: Optional[Color] = Color("white"),
        scale: float = 1.0,
    ) -> None:
        """
        Draw icons in the form of table.

        :param file_name: output SVG file name
        :param columns: number of columns in grid
        :param step: horizontal and vertical distance between icons in grid
        :param background_color: background color
        :param scale: scale icon by the magnitude
        """
        point: np.ndarray = np.array((step / 2.0 * scale, step / 2.0 * scale))
        width: float = step * columns * scale

        height: int = int(int(len(self.icons) / columns + 1.0) * step * scale)
        svg: Drawing = Drawing(str(file_name), (width, height))
        if background_color is not None:
            svg.add(
                svg.rect((0, 0), (width, height), fill=background_color.hex)
            )

        for icon in self.icons:
            icon.draw(svg, point, scale=scale)
            point += np.array((step * scale, 0.0))
            if point[0] > width - 8.0:
                point[0] = step / 2.0 * scale
                point += np.array((0.0, step * scale))
                height += step * scale

        with file_name.open("w", encoding="utf-8") as output_file:
            svg.write(output_file)

    def __len__(self) -> int:
        return len(self.icons)

    def sort(self) -> None:
        """Sort icon list."""
        self.icons = sorted(self.icons)


def draw_icons() -> None:
    """
    Draw all possible icon shapes combinations as grid in one SVG file and as
    individual SVG files.
    """
    scheme: Scheme = Scheme.from_file(workspace.DEFAULT_SCHEME_PATH)
    extractor: ShapeExtractor = ShapeExtractor(
        workspace.ICONS_PATH, workspace.ICONS_CONFIG_PATH
    )
    collection: IconCollection = IconCollection.from_scheme(scheme, extractor)
    collection.sort()

    # Draw individual icons.

    icons_by_id_path: Path = workspace.get_icons_by_id_path()
    collection.draw_icons(icons_by_id_path, workspace.ICONS_LICENSE_PATH)

    icons_by_name_path: Path = workspace.get_icons_by_name_path()
    collection.draw_icons(
        icons_by_name_path, workspace.ICONS_LICENSE_PATH, by_name=True
    )

    logging.info(
        f"Icons are written to {icons_by_name_path} and {icons_by_id_path}."
    )

    # Draw grid.

    for icon in collection.icons:
        icon.recolor(Color("#444444"))

    for path, scale in (
        (workspace.get_icon_grid_path(), 1.0),
        (workspace.GRID_PATH, 2.0),
    ):
        collection.draw_grid(path, scale=scale)
        logging.info(f"Icon grid is written to {path}.")
