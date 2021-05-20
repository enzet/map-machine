"""
Icon grid drawing.

Author: Sergey Vartanov (me@enzet.ru).
"""
from os.path import join
from pathlib import Path
from typing import Any, Dict, List, Set

import numpy as np
from colour import Color
from svgwrite import Drawing

from roentgen.icon import Icon, ShapeExtractor, ShapeSpecification
from roentgen.scheme import Scheme


def draw_all_icons(
    output_file_name: str, output_directory: str, columns: int = 16,
    step: float = 24, background_color: Color = Color("white"),
    color: Color = Color("black")
) -> None:
    """
    Draw all possible icon combinations in grid.

    :param output_file_name: output SVG file name for icon grid
    :param output_directory: path to the directory to store individual SVG files
        for icons
    :param columns: the number of columns in grid
    :param step: horizontal and vertical distance between icons
    :param background_color: background color
    :param color: icon color
    """
    tags_file_name: str = "scheme/default.yml"
    scheme: Scheme = Scheme(tags_file_name)

    icons: List[Icon] = []

    icons_file_name: str = "icons/icons.svg"
    extractor: ShapeExtractor = ShapeExtractor(
        icons_file_name, Path("icons/config.json")
    )

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

    for element in scheme.icons:  # type: Dict[str, Any]
        for key in ["icon", "add_icon"]:
            if key in element:
                current_set = element[key]
                add()
        if "over_icon" not in element:
            continue
        if "under_icon" in element:
            for icon_id in element["under_icon"]:  # type: str
                current_set = set([icon_id] + element["over_icon"])
                add()
        if not ("under_icon" in element and "with_icon" in element):
            continue
        for icon_id in element["under_icon"]:  # type: str
            for icon_2_id in element["with_icon"]:  # type: str
                current_set: Set[str] = set(
                    [icon_id] + [icon_2_id] + element["over_icon"])
                add()
            for icon_2_id in element["with_icon"]:  # type: str
                for icon_3_id in element["with_icon"]:  # type: str
                    current_set = set(
                        [icon_id] + [icon_2_id] + [icon_3_id] +
                        element["over_icon"])
                    if (icon_2_id != icon_3_id and icon_2_id != icon_id and
                            icon_3_id != icon_id):
                        add()

    specified_ids: Set[str] = set()

    for icon in icons:
        specified_ids |= icon.get_shape_ids()
    print(
        "Icons with no tag specification: \n    " +
        ", ".join(sorted(extractor.shapes.keys() - specified_ids)) + "."
    )

    for icon in icons:  # type: Icon
        icon.draw_to_file(join(
            output_directory, f"{' + '.join(icon.get_names())}.svg"
        ))

    draw_grid(
        output_file_name, icons, columns, step,
        background_color=background_color
    )


def draw_grid(
    file_name: str, icons: List[Icon], columns: int = 16, step: float = 24,
    background_color: Color = Color("white")
):
    """
    Draw icons in the form of table

    :param file_name: output SVG file name
    :param icons: list of icons
    :param columns: number of columns in grid
    :param step: horizontal and vertical distance between icons in grid
    :param background_color: background color
    """
    point: np.array = np.array((step / 2, step / 2))
    width: float = step * columns

    height: int = int(int(len(icons) / (width / step) + 1) * step)
    svg: Drawing = Drawing(file_name, (width, height))
    svg.add(svg.rect((0, 0), (width, height), fill=background_color.hex))

    for icon in icons:
        icon: Icon
        svg.add(svg.rect(
            point - np.array((10, 10)), (20, 20),
            fill=background_color.hex
        ))
        icon.draw(svg, point)
        point += np.array((step, 0))
        if point[0] > width - 8:
            point[0] = step / 2
            point += np.array((0, step))
            height += step

    print(f"Icons: {len(icons)}.")

    with open(file_name, "w") as output_file:
        svg.write(output_file)
