from dataclasses import dataclass
from typing import Dict, Optional, List

import numpy as np
import svgwrite
from colour import Color

from roentgen.address import get_address
from roentgen.color import is_bright
from roentgen.icon import Icon
from roentgen.osm_reader import Tagged
from roentgen.scheme import IconSet

DEFAULT_FONT: str = "Roboto"
DEFAULT_COLOR: Color = Color("#444444")


@dataclass
class TextStruct:
    """
    Some label on the map with attributes.
    """
    text: str
    fill: Color = DEFAULT_COLOR
    size: float = 10.0


def draw_point_shape(
        svg: svgwrite.Drawing, icons: List[Icon], point, fill: Color,
        tags=None):
    """
    Draw one combined icon and its outline.
    """
    # Down-cast floats to integers to make icons pixel-perfect.
    point = np.array(list(map(int, point)))

    # Draw outlines.

    for icon in icons:  # type: Icon
        bright: bool = is_bright(fill)
        color: Color = Color("black") if bright else Color("white")
        opacity: float = 0.7 if bright else 0.5
        icon.draw(svg, point, color, opacity=opacity, outline=True)

    # Draw icons.

    for icon in icons:  # type: Icon
        icon.draw(svg, point, fill, tags=tags)


def draw_text(
        svg: svgwrite.Drawing, text: str, point, fill: Color,
        size: float = 10.0, out_fill=Color("white"), out_opacity=1.0,
        out_fill_2: Optional[Color] = None, out_opacity_2=1.0):
    """
    Drawing text.

      ######     ###  outline 2
     #------#    ---  outline 1
    #| Text |#
     #------#
      ######
    """
    if out_fill_2:
        svg.add(svg.text(
            text, point, font_size=size, text_anchor="middle",
            font_family=DEFAULT_FONT, fill=out_fill_2.hex,
            stroke_linejoin="round", stroke_width=5,
            stroke=out_fill_2.hex, opacity=out_opacity_2))
    if out_fill:
        svg.add(svg.text(
            text, point, font_size=size, text_anchor="middle",
            font_family=DEFAULT_FONT, fill=out_fill.hex,
            stroke_linejoin="round", stroke_width=3,
            stroke=out_fill.hex, opacity=out_opacity))
    svg.add(svg.text(
        text, point, font_size=size, text_anchor="middle",
        font_family=DEFAULT_FONT, fill=fill.hex))


def construct_text(
        tags, processed, scheme, draw_captions) -> List["TextStruct"]:
    """
    Construct labels for not processed tags.
    """
    texts: List[TextStruct] = []

    name = None
    alt_name = None
    if "name" in tags:
        name = tags["name"]
        tags.pop("name", None)
    if "name:ru" in tags:
        if not name:
            name = tags["name:ru"]
            tags.pop("name:ru", None)
        tags.pop("name:ru", None)
    if "name:en" in tags:
        if not name:
            name = tags["name:en"]
            tags.pop("name:en", None)
        tags.pop("name:en", None)
    if "alt_name" in tags:
        if alt_name:
            alt_name += ", "
        else:
            alt_name = ""
        alt_name += tags["alt_name"]
        tags.pop("alt_name")
    if "old_name" in tags:
        if alt_name:
            alt_name += ", "
        else:
            alt_name = ""
        alt_name += "бывш. " + tags["old_name"]

    address: List[str] = get_address(tags, draw_captions)

    if name:
        texts.append(TextStruct(name, Color("black")))
    if alt_name:
        texts.append(TextStruct(f"({alt_name})"))
    if address:
        texts.append(TextStruct(", ".join(address)))

    if draw_captions == "main":
        return texts

    if "route_ref" in tags:
        texts.append(TextStruct(tags["route_ref"].replace(";", " ")))
        tags.pop("route_ref", None)
    if "cladr:code" in tags:
        texts.append(TextStruct(tags["cladr:code"], size=7))
        tags.pop("cladr:code", None)
    if "website" in tags:
        link = tags["website"]
        if link[:7] == "http://":
            link = link[7:]
        if link[:8] == "https://":
            link = link[8:]
        if link[:4] == "www.":
            link = link[4:]
        if link[-1] == "/":
            link = link[:-1]
        link = link[:25] + ("..." if len(tags["website"]) > 25 else "")
        texts.append(TextStruct(link, Color("#000088")))
        tags.pop("website", None)
    for k in ["phone"]:
        if k in tags:
            texts.append(TextStruct(tags[k], Color("#444444")))
            tags.pop(k)
    for tag in tags:
        if scheme.is_writable(tag) and not (tag in processed):
            texts.append(TextStruct(tags[tag]))
    return texts


class Point(Tagged):
    """
    Object on the map with no dimensional attributes.

    It may have icons and text.
    """
    def __init__(
            self, icon_set: IconSet, tags: Dict[str, str], point: np.array,
            coordinates: np.array, priority: float = 0,
            is_for_node: bool = True):
        super().__init__()

        assert point is not None

        self.icon_set: IconSet = icon_set
        self.tags: Dict[str, str] = tags
        self.point: np.array = point
        self.coordinates: np.array = coordinates
        self.priority: float = priority
        self.layer: float = 0
        self.is_for_node: bool = is_for_node

        self.y = 0

    def draw_shapes(self, svg: svgwrite.Drawing):
        """
        Draw shapes for one node.
        """
        if self.icon_set.main_icon and (not self.icon_set.main_icon[0].is_default() or self.is_for_node):
            draw_point_shape(
                svg, self.icon_set.main_icon,
                self.point + np.array((0, self.y)), self.icon_set.color,
                tags=self.tags)
            self.y += 16

        left: float = -(len(self.icon_set.extra_icons) - 1) * 8

        for shape_ids in self.icon_set.extra_icons:
            draw_point_shape(
                svg, shape_ids, self.point + np.array((left, self.y)),
                Color("#888888"))
            left += 16

        if self.icon_set.extra_icons:
            self.y += 16

    def draw_texts(self, svg: svgwrite.Drawing, scheme, draw_captions):
        """
        Draw all labels.
        """
        write_tags = construct_text(
            self.tags, self.icon_set.processed, scheme, draw_captions)

        for text_struct in write_tags:  # type: TextStruct
            self.y += text_struct.size + 1
            text = text_struct.text
            text = text.replace("&quot;", '"')
            text = text.replace("&amp;", '&')
            text = text[:26] + ("..." if len(text) > 26 else "")
            draw_text(
                svg, text, self.point + np.array((0, self.y - 8)),
                text_struct.fill, size=text_struct.size)
