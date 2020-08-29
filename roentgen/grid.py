"""
Author: Sergey Vartanov (me@enzet.ru).
"""

import os
import random
import yaml

from roentgen import extract_icon
from roentgen import svg

from typing import Any, Dict


def draw_icon(
        output_file, icon: Dict[str, Any], x: float, y: float,
        color: str = "444444"):

    output_file.write(
        f'<path d="{icon["path"]}" '
        f'style="fill:#{color};stroke:none;" '
        f'transform="translate({icon["x"] + x},{icon["y"] + y})" />\n')


def draw_grid():
    tags_file_name = "data/tags.yml"

    scheme = yaml.load(open(tags_file_name), Loader=yaml.FullLoader)

    icons_file_name = "icons/icons.svg"
    icon_grid_file_name = "icon_grid.svg"
    icon_colors_file_name = "data/icon_colors"

    icon_colors = [("FFFFFF", "444444")]

    if os.path.isfile(icon_colors_file_name):
        icon_colors_file = open(icon_colors_file_name)
        for line in icon_colors_file.read().split("\n"):
            background_color = \
                hex(int(line[0:3]))[2:] + hex(int(line[3:6]))[2:] + \
                hex(int(line[6:9]))[2:]
            foreground_color = \
                hex(int(line[10:13]))[2:] + hex(int(line[13:16]))[2:] + \
                hex(int(line[16:19]))[2:]
            icon_colors.append((background_color, foreground_color))

    step: float = 24

    width: float = 24 * 16

    x: float = step / 2
    y: float = step / 2

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

    icons = []

    extractor = extract_icon.IconExtractor(icons_file_name)

    for icons_to_draw in to_draw:
        drawed = False
        icon_set = {"icons": []}
        for icon in icons_to_draw:
            path, xx, yy, _ = extractor.get_path(icon)
            icon_set["icons"].append({"path": path,
                "x": (- 8.0 - xx * 16),
                "y": (- 8.0 - yy * 16)})
            drawed = True
        if drawed:
            icons.append(icon_set)
            number += 1

    height = int(number / (width / step) + 1) * step

    output_file = svg.SVG(open(icon_grid_file_name, "w+"))
    output_file.begin(width, height)

    output_file.rect(0, 0, width, height, color="FFFFFF")

    for icon in icons:
        background_color, foreground_color = random.choice(icon_colors)
        output_file.rect(x - 2 - 8, y - 2 - 8, 20, 20, color=background_color)
        for i in icon["icons"]:
            draw_icon(output_file, i, x, y, foreground_color)
        x += step
        if x > width - 8:
            x = step / 2
            y += step
            height += step

    print(f"Icons: {number}.")

    output_file.end()
