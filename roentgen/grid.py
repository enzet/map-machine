"""
Icon grid drawing.
"""
from pathlib import Path
from typing import List, Set

import numpy as np
from colour import Color
from svgwrite import Drawing

from roentgen.icon import Icon, ShapeExtractor, ShapeSpecification
from roentgen.scheme import Scheme

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


class IconCollection:
    def __init__(self, icons):
        self.icons: List[Icon] = icons

    @classmethod
    def from_scheme(
        cls,
        scheme: Scheme,
        extractor: ShapeExtractor,
        background_color: Color = Color("white"),
        color: Color = Color("black")
    ) -> "IconCollection":
        """
        Draw all possible icon combinations in grid.

        :param scheme: tag specification
        :param extractor: shape extractor for icon creation
        :param background_color: background color
        :param color: icon color
        """
        icons: List[Icon] = []

        def add() -> None:
            """
            Construct icon and add it to the list.
            """
            specifications = [
                ShapeSpecification.from_structure(x, extractor, scheme)
                for x in current_set
            ]
            constructed_icon: Icon = Icon(specifications)
            constructed_icon.recolor(color, white=background_color)
            if constructed_icon not in icons:
                icons.append(constructed_icon)

        for matcher in scheme.node_matchers:
            if matcher.shapes:
                current_set = matcher.shapes
                add()
            if matcher.add_shapes:
                current_set = matcher.add_shapes
                add()
            if not matcher.over_icon:
                continue
            if matcher.under_icon:
                for icon_id in matcher.under_icon:
                    current_set = [icon_id] + matcher.over_icon
                    add()
            if not (matcher.under_icon and matcher.with_icon):
                continue
            for icon_id in matcher.under_icon:
                for icon_2_id in matcher.with_icon:
                    current_set: List[str] = (
                        [icon_id] + [icon_2_id] + matcher.over_icon
                    )
                    add()
                for icon_2_id in matcher.with_icon:
                    for icon_3_id in matcher.with_icon:
                        current_set = (
                            [icon_id] + [icon_2_id] + [icon_3_id] +
                            matcher.over_icon
                        )
                        if (icon_2_id != icon_3_id and icon_2_id != icon_id and
                                icon_3_id != icon_id):
                            add()

        specified_ids: Set[str] = set()

        for icon in icons:
            specified_ids |= set(icon.get_shape_ids())
        print(
            "Icons with no tag specification: \n    " +
            ", ".join(sorted(extractor.shapes.keys() - specified_ids)) + "."
        )
        return cls(icons)

    def draw_icons(self, output_directory: Path):
        """
        :param output_directory: path to the directory to store individual SVG files
            for icons
        """
        for icon in self.icons:
            icon.draw_to_file(
                output_directory / f"{'___'.join(icon.get_shape_ids())}.svg"
            )

    def draw_grid(
        self,
        file_name: Path,
        columns: int = 16,
        step: float = 24,
        background_color: Color = Color("white"),
    ):
        """
        Draw icons in the form of table.

        :param file_name: output SVG file name
        :param columns: number of columns in grid
        :param step: horizontal and vertical distance between icons in grid
        :param background_color: background color
        """
        point: np.array = np.array((step / 2, step / 2))
        width: float = step * columns

        height: int = int(int(len(self.icons) / (width / step) + 1) * step)
        svg: Drawing = Drawing(str(file_name), (width, height))
        svg.add(svg.rect((0, 0), (width, height), fill=background_color.hex))

        for icon in self.icons:
            icon: Icon
            rectangle = svg.rect(
                point - np.array((10, 10)), (20, 20),
                fill=background_color.hex
            )
            svg.add(rectangle)
            icon.draw(svg, point)
            point += np.array((step, 0))
            if point[0] > width - 8:
                point[0] = step / 2
                point += np.array((0, step))
                height += step

        with open(file_name, "w") as output_file:
            svg.write(output_file)

    def __len__(self) -> int:
        return len(self.icons)
