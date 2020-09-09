"""
Icon grid drawing.

Author: Sergey Vartanov (me@enzet.ru).
"""
import numpy as np
from svgwrite import Drawing
import yaml

from roentgen.extract_icon import Icon, IconExtractor

from typing import List


def draw_grid(step: float = 24, columns: int = 16):
    """
    Draw all possible icon combinations in grid.

    :param step: horizontal and vertical distance between icons
    :param columns: the number of columns in grid
    """
    tags_file_name = "data/tags.yml"

    scheme = yaml.load(open(tags_file_name), Loader=yaml.FullLoader)

    icons_file_name = "icons/icons.svg"
    icon_grid_file_name = "icon_grid.svg"

    width: float = step * columns
    point: np.array = np.array((step / 2, step / 2))

    to_draw = []

    for element in scheme["tags"]:
        if "icon" in element:
            if set(element["icon"]) not in to_draw:
                to_draw.append(set(element["icon"]))
        if "add_icon" in element:
            if set(element["add_icon"]) not in to_draw:
                to_draw.append(set(element["add_icon"]))
        if "over_icon" not in element:
            continue
        if "under_icon" in element:
            for icon in element["under_icon"]:
                current_set = set([icon] + element["over_icon"])
                if current_set not in to_draw:
                    to_draw.append(current_set)
        if not ("under_icon" in element and "with_icon" in element):
            continue
        for icon in element["under_icon"]:
            for icon2 in element["with_icon"]:
                current_set = set([icon] + [icon2] + element["over_icon"])
                if current_set not in to_draw:
                    to_draw.append(current_set)
            for icon2 in element["with_icon"]:
                for icon3 in element["with_icon"]:
                    current_set = \
                        set([icon] + [icon2] + [icon3] + element["over_icon"])
                    if icon2 != icon3 and icon2 != icon and icon3 != icon and \
                            (current_set not in to_draw):
                        to_draw.append(current_set)

    number: int = 0

    icons: List[List[Icon]] = []

    extractor: IconExtractor = IconExtractor(icons_file_name)

    for icons_to_draw in to_draw:
        found: bool = False
        icon_set: List[Icon] = []
        for icon_id in icons_to_draw:  # type: str
            icon, got = extractor.get_path(icon_id)
            assert got
            icon_set.append(icon)
            found = True
        if found:
            icons.append(icon_set)
            number += 1

    height: int = int(int(number / (width / step) + 1) * step)

    svg: Drawing = Drawing(icon_grid_file_name, (width, height))

    svg.add(svg.rect((0, 0), (width, height), fill="#FFFFFF"))

    for icon in icons:
        background_color, foreground_color = "#FFFFFF", "#444444"
        svg.add(svg.rect(
            point - np.array((-10, -10)), (20, 20),
            fill=background_color))
        for i in icon:  # type: Icon
            path = i.get_path(svg, point)
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
