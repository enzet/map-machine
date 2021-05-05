from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import svgwrite
from colour import Color

from roentgen.color import is_bright
from roentgen.icon import Shape
from roentgen.osm_reader import Tagged
from roentgen.scheme import Icon, Scheme
from roentgen.text import get_address, get_text

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


class Occupied:
    def __init__(self, width: int, height: int, overlap: float):
        self.matrix = np.full((int(width), int(height)), False, dtype=bool)
        self.width = width
        self.height = height
        self.overlap = overlap

    def check(self, point) -> bool:
        if 0 <= point[0] < self.width and 0 <= point[1] < self.height:
            return self.matrix[point[0], point[1]] == True
        return True

    def register(self, point) -> None:
        if 0 <= point[0] < self.width and 0 <= point[1] < self.height:
            self.matrix[point[0], point[1]] = True
            assert self.matrix[point[0], point[1]] == True


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
        alt_name += "ex " + tags["old_name"]

    address: List[str] = get_address(tags, draw_captions)

    if name:
        texts.append(TextStruct(name, Color("black")))
    if alt_name:
        texts.append(TextStruct(f"({alt_name})"))
    if address:
        texts.append(TextStruct(", ".join(address)))

    if draw_captions == "main":
        return texts

    for text in get_text(tags):  # type: str
        if text:
            texts.append(TextStruct(text))

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


def in_range(position, points) -> bool:
    return 0 <= position[0] < len(points) and 0 <= position[1] < len(points[0])


class Point(Tagged):
    """
    Object on the map with no dimensional attributes.

    It may have icons and text.
    """

    def __init__(
        self, icon: Icon, tags: Dict[str, str], point: np.array,
        coordinates: np.array, priority: float = 0,
        is_for_node: bool = True, draw_outline: bool = True
    ):
        super().__init__()

        assert point is not None

        self.icon: Icon = icon
        self.tags: Dict[str, str] = tags
        self.point: np.array = point
        self.coordinates: np.array = coordinates
        self.priority: float = priority
        self.layer: float = 0
        self.is_for_node: bool = is_for_node
        self.draw_outline: bool = draw_outline

        self.y = 0
        self.main_icon_painted: bool = False

    def draw_main_shapes(
        self, svg: svgwrite.Drawing, occupied: Optional[Occupied] = None
    ) -> None:
        """
        Draw main shape for one node.
        """
        if (
            self.icon.main_icon and
            (not self.icon.main_icon[0].is_default() or
             self.is_for_node)
        ):
            position = self.point + np.array((0, self.y))
            self.main_icon_painted: bool = self.draw_point_shape(
                svg, self.icon.main_icon,
                position, self.icon.color, occupied,
                tags=self.tags)
            if self.main_icon_painted:
                self.y += 16

    def draw_extra_shapes(
        self, svg: svgwrite.Drawing, occupied: Optional[Occupied] = None
    ) -> None:
        """
        Draw secondary shapes.
        """
        if not self.icon.extra_icons or not self.main_icon_painted:
            return

        is_place_for_extra: bool = True
        if occupied:
            left: float = -(len(self.icon.extra_icons) - 1) * 8
            for _ in self.icon.extra_icons:
                if occupied.check(
                    (int(self.point[0] + left), int(self.point[1] + self.y))
                ):
                    is_place_for_extra = False
                    break
                left += 16

        if is_place_for_extra:
            left: float = -(len(self.icon.extra_icons) - 1) * 8
            for shape_ids in self.icon.extra_icons:
                self.draw_point_shape(
                    svg, shape_ids, self.point + np.array((left, self.y)),
                    Color("#888888"), occupied)
                left += 16
            if self.icon.extra_icons:
                self.y += 16

    def draw_point_shape(
        self, svg: svgwrite.Drawing, shapes: List[Shape], position,
        fill: Color, occupied, tags: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Draw one combined icon and its outline.
        """
        # Down-cast floats to integers to make icons pixel-perfect.
        position = list(map(int, position))

        if occupied and occupied.check(position):
            return False

        # Draw outlines.

        if self.draw_outline:
            for icon in shapes:  # type: Shape
                bright: bool = is_bright(fill)
                color: Color = Color("black") if bright else Color("white")
                opacity: float = 0.7 if bright else 0.5
                icon.draw(svg, position, color, opacity=opacity, outline=True)

        # Draw icons.

        for icon in shapes:  # type: Shape
            icon.draw(svg, position, fill, tags=tags)

        if occupied:
            overlap: int = occupied.overlap
            for i in range(-overlap, overlap):
                for j in range(-overlap, overlap):
                    occupied.register((position[0] + i, position[1] + j))

        return True

    def draw_texts(
            self, svg: svgwrite.Drawing, scheme: Scheme, occupied: Occupied,
            draw_captions):
        """
        Draw all labels.
        """
        text_structures: List[TextStruct] = construct_text(
            self.tags, self.icon.processed, scheme, draw_captions)

        for text_struct in text_structures:  # type: TextStruct
            text = text_struct.text
            text = text.replace("&quot;", '"')
            text = text.replace("&amp;", '&')
            text = text[:26] + ("..." if len(text) > 26 else "")
            self.draw_text(
                svg, text, self.point + np.array((0, self.y)),
                occupied, text_struct.fill, size=text_struct.size
            )

    def draw_text(
        self, svg: svgwrite.Drawing, text: str, point, occupied: Occupied,
        fill: Color, size: float = 10.0, out_fill=Color("white"),
        out_opacity: float = 0.5, out_fill_2: Optional[Color] = None,
        out_opacity_2: float = 1.0
    ) -> None:
        """
        Drawing text.

          ######     ###  outline 2
         #------#    ---  outline 1
        #| Text |#
         #------#
          ######
        """
        length = len(text) * 6

        if occupied:
            is_occupied: bool = False
            for i in range(-int(length / 2), int(length / 2)):
                if occupied.check((int(point[0] + i), int(point[1] - 4))):
                    is_occupied = True
                    break

            if is_occupied:
                return

            for i in range(-int(length / 2), int(length / 2)):
                for j in range(-12, 5):
                    occupied.register((int(point[0] + i), int(point[1] + j)))
                    # svg.add(svg.rect((point[0] + i, point[1] + j), (1, 1)))

        if out_fill_2:
            svg.add(svg.text(
                text, point, font_size=size, text_anchor="middle",
                font_family=DEFAULT_FONT, fill=out_fill_2.hex,
                stroke_linejoin="round", stroke_width=5,
                stroke=out_fill_2.hex, opacity=out_opacity_2
            ))
        if out_fill:
            svg.add(svg.text(
                text, point, font_size=size, text_anchor="middle",
                font_family=DEFAULT_FONT, fill=out_fill.hex,
                stroke_linejoin="round", stroke_width=3,
                stroke=out_fill.hex, opacity=out_opacity
            ))
        svg.add(svg.text(
            text, point, font_size=size, text_anchor="middle",
            font_family=DEFAULT_FONT, fill=fill.hex
        ))

        self.y += 11
