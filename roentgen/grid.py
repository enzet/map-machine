"""
Icon grid drawing.

Author: Sergey Vartanov (me@enzet.ru).
"""
import numpy as np
from svgwrite import Drawing
from typing import List, Dict, Any, Set

from roentgen.icon import Icon, IconExtractor
from roentgen.scheme import Scheme


def draw_grid(step: float = 24, columns: int = 16):
    """
    Draw all possible icon combinations in grid.

    :param step: horizontal and vertical distance between icons
    :param columns: the number of columns in grid
    """
    tags_file_name: str = "data/tags.yml"

    scheme: Scheme = Scheme(tags_file_name)

    icons_file_name: str = "icons/icons.svg"
    icon_grid_file_name: str = "icon_grid.svg"

    width: float = step * columns
    point: np.array = np.array((step / 2, step / 2))

    to_draw: List[Set[str]] = []

    for element in scheme.icons:  # type: Dict[str, Any]
        if "icon" in element:
            if set(element["icon"]) not in to_draw:
                to_draw.append(set(element["icon"]))
        if "add_icon" in element:
            if set(element["add_icon"]) not in to_draw:
                to_draw.append(set(element["add_icon"]))
        if "over_icon" not in element:
            continue
        if "under_icon" in element:
            for icon_id in element["under_icon"]:  # type: str
                current_set = set([icon_id] + element["over_icon"])
                if current_set not in to_draw:
                    to_draw.append(current_set)
        if not ("under_icon" in element and "with_icon" in element):
            continue
        for icon_id in element["under_icon"]:  # type: str
            for icon_2_id in element["with_icon"]:  # type: str
                current_set: Set[str] = set(
                    [icon_id] + [icon_2_id] + element["over_icon"])
                if current_set not in to_draw:
                    to_draw.append(current_set)
            for icon_2_id in element["with_icon"]:  # type: str
                for icon_3_id in element["with_icon"]:  # type: str
                    current_set = set(
                        [icon_id] + [icon_2_id] + [icon_3_id] +
                        element["over_icon"])
                    if (icon_2_id != icon_3_id and icon_2_id != icon_id and
                            icon_3_id != icon_id and
                            (current_set not in to_draw)):
                        to_draw.append(current_set)

    number: int = 0

    icons: List[List[Icon]] = []

    extractor: IconExtractor = IconExtractor(icons_file_name)

    for icons_to_draw in to_draw:
        found: bool = False
        icon_set: List[Icon] = []
        for icon_id in icons_to_draw:  # type: str
            icon, extracted = extractor.get_path(icon_id)  # type: Icon, bool
            assert extracted, f"no icon with ID {icon_id}"
            icon_set.append(icon)
            found = True
        if found:
            icons.append(icon_set)
            number += 1

    height: int = int(int(number / (width / step) + 1) * step)

    svg: Drawing = Drawing(icon_grid_file_name, (width, height))

    svg.add(svg.rect((0, 0), (width, height), fill="#FFFFFF"))

    for combined_icon in icons:  # type: List[Icon]
        background_color, foreground_color = "#FFFFFF", "#444444"
        svg.add(svg.rect(
            point - np.array((-10, -10)), (20, 20),
            fill=background_color))
        for icon in combined_icon:  # type: Icon
            path = icon.get_path(svg, point)
            path.update({"fill": foreground_color})
            svg.add(path)
        point += np.array((step, 0))
        if point[0] > width - 8:
            point[0] = step / 2
            point += np.array((0, step))
            height += step

    print(f"Icons: {number}.")

    with open(icon_grid_file_name, "w") as output_file:
        svg.write(output_file)
