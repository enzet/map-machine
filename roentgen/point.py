from typing import Dict, List, Optional

import numpy as np
import svgwrite
from colour import Color

from roentgen.color import is_bright
from roentgen.icon import Shape
from roentgen.osm_reader import Tagged
from roentgen.scheme import Icon
from roentgen.text import Label

DEFAULT_FONT: str = "Roboto"


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


def in_range(position, points) -> bool:
    return 0 <= position[0] < len(points) and 0 <= position[1] < len(points[0])


class Point(Tagged):
    """
    Object on the map with no dimensional attributes.

    It may have icons and text.
    """

    def __init__(
        self, icon: Icon, labels: List[Label], tags: Dict[str, str],
        point: np.array, coordinates: np.array, priority: float = 0,
        is_for_node: bool = True, draw_outline: bool = True
    ):
        super().__init__()

        assert point is not None

        self.icon: Icon = icon
        self.labels: List[Label] = labels
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

    def draw_texts(self, svg: svgwrite.Drawing, occupied: Occupied) -> None:
        """
        Draw all labels.
        """
        for text_struct in self.labels:  # type: Label
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
