"""
Point: node representation on the map.
"""
from typing import Optional

import numpy as np
import svgwrite
from colour import Color

from roentgen.icon import Icon, IconSet
from roentgen.osm_reader import Tagged
from roentgen.text import Label

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

DEFAULT_FONT: str = "Roboto"


class Occupied:
    """
    Structure that remembers places of the canvas occupied by elements (icons,
    texts, shapes).
    """

    def __init__(self, width: int, height: int, overlap: float) -> None:
        self.matrix = np.full((int(width), int(height)), False, dtype=bool)
        self.width: float = width
        self.height: float = height
        self.overlap: float = overlap

    def check(self, point: np.array) -> bool:
        """
        Check whether point is already occupied by other elements.
        """
        if 0 <= point[0] < self.width and 0 <= point[1] < self.height:
            return self.matrix[point[0], point[1]]
        return True

    def register(self, point) -> None:
        """
        Register that point is occupied by an element.
        """
        if 0 <= point[0] < self.width and 0 <= point[1] < self.height:
            self.matrix[point[0], point[1]] = True
            assert self.matrix[point[0], point[1]]


class Point(Tagged):
    """
    Object on the map with no dimensional attributes.

    It may have icons and labels.
    """

    def __init__(
        self,
        icon_set: IconSet,
        labels: list[Label],
        tags: dict[str, str],
        processed: set[str],
        point: np.array,
        coordinates: np.array,
        priority: float = 0,
        is_for_node: bool = True,
        draw_outline: bool = True,
    ) -> None:
        super().__init__()

        assert point is not None

        self.icon_set: IconSet = icon_set
        self.labels: list[Label] = labels
        self.tags: dict[str, str] = tags
        self.processed: set[str] = processed
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
        keys_left = [x for x in self.tags.keys() if x not in self.processed]
        if (
            self.icon_set.main_icon.is_default()
            and not self.icon_set.extra_icons
            and (not keys_left or not self.is_for_node)
        ):
            return

        position = self.point + np.array((0, self.y))
        self.main_icon_painted: bool = self.draw_point_shape(
            svg, self.icon_set.main_icon, position, occupied, tags=self.tags
        )
        if self.main_icon_painted:
            self.y += 16

    def draw_extra_shapes(
        self, svg: svgwrite.Drawing, occupied: Optional[Occupied] = None
    ) -> None:
        """
        Draw secondary shapes.
        """
        if not self.icon_set.extra_icons or not self.main_icon_painted:
            return

        is_place_for_extra: bool = True
        if occupied:
            left: float = -(len(self.icon_set.extra_icons) - 1) * 8
            for _ in self.icon_set.extra_icons:
                if occupied.check(
                    (int(self.point[0] + left), int(self.point[1] + self.y))
                ):
                    is_place_for_extra = False
                    break
                left += 16

        if is_place_for_extra:
            left: float = -(len(self.icon_set.extra_icons) - 1) * 8
            for icon in self.icon_set.extra_icons:
                point: np.array = self.point + np.array((left, self.y))
                self.draw_point_shape(svg, icon, point, occupied=occupied)
                left += 16
            if self.icon_set.extra_icons:
                self.y += 16

    def draw_point_shape(
        self,
        svg: svgwrite.Drawing,
        icon: Icon,
        position,
        occupied,
        tags: Optional[dict[str, str]] = None,
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
            icon.draw(svg, position, outline=True)

        # Draw icons.

        icon.draw(svg, position, tags=tags)

        if occupied:
            overlap: int = occupied.overlap
            for i in range(-overlap, overlap):
                for j in range(-overlap, overlap):
                    occupied.register((position[0] + i, position[1] + j))

        return True

    def draw_texts(
        self,
        svg: svgwrite.Drawing,
        occupied: Optional[Occupied] = None,
        label_mode: str = "main",
    ) -> None:
        """
        Draw all labels.
        """
        labels: list[Label]

        if label_mode == "main":
            labels = self.labels[:1]
        elif label_mode == "all":
            labels = self.labels
        else:
            return

        for label in labels:
            text = label.text
            text = text.replace("&quot;", '"')
            text = text.replace("&amp;", "&")
            text = text[:26] + ("..." if len(text) > 26 else "")
            point = self.point + np.array((0, self.y + 2))
            self.draw_text(
                svg, text, point, occupied, label.fill, size=label.size
            )

    def draw_text(
        self,
        svg: svgwrite.Drawing,
        text: str,
        point,
        occupied: Optional[Occupied],
        fill: Color,
        size: float = 10.0,
        out_fill=Color("white"),
        out_opacity: float = 0.5,
        out_fill_2: Optional[Color] = None,
        out_opacity_2: float = 1.0,
        is_debug: bool = False,
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
                    if is_debug:
                        svg.add(svg.rect((point[0] + i, point[1] + j), (1, 1)))

        if out_fill_2:
            text_element = svg.text(
                text, point, font_size=size, text_anchor="middle",
                font_family=DEFAULT_FONT, fill=out_fill_2.hex,
                stroke_linejoin="round", stroke_width=5, stroke=out_fill_2.hex,
                opacity=out_opacity_2
            )  # fmt: skip
            svg.add(text_element)
        if out_fill:
            text_element = svg.text(
                text, point, font_size=size, text_anchor="middle",
                font_family=DEFAULT_FONT, fill=out_fill.hex,
                stroke_linejoin="round", stroke_width=3, stroke=out_fill.hex,
                opacity=out_opacity,
            )  # fmt: skip
            svg.add(text_element)
        text_element = svg.text(
            text, point, font_size=size, text_anchor="middle",
            font_family=DEFAULT_FONT, fill=fill.hex,
        )  # fmt: skip
        svg.add(text_element)

        self.y += 11

    def get_size(self) -> np.array:
        """
        Get width and height of the point visual representation if there is
        space for all elements.
        """
        icon_size: int = 16
        width: int = icon_size * (
            1 + max(2, len(self.icon_set.extra_icons) - 1)
        )
        height: int = icon_size * (1 + int(len(self.icon_set.extra_icons) / 3))
        if len(self.labels):
            height += 4 + 11 * len(self.labels)
        return np.array((width, height))
