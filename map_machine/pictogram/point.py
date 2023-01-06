"""Point: node representation on the map."""
import logging
from typing import Optional

import numpy as np
import svgwrite
from colour import Color

from map_machine.drawing import draw_text
from map_machine.map_configuration import LabelMode
from map_machine.osm.osm_reader import Tagged
from map_machine.pictogram.icon import Icon, IconSet
from map_machine.text import Label

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


class Occupied:
    """
    Structure that remembers places of the canvas occupied by elements (icons,
    texts, shapes).
    """

    def __init__(self, width: int, height: int, overlap: int) -> None:
        self.matrix = np.full((int(width), int(height)), False, dtype=bool)
        try:
            self.matrix = np.full((int(width), int(height)), False, dtype=bool)
        except Exception:
            logging.fatal(
                "Failed to allocate a matrix required by overlap algorithm. "
                "Try to use smallest area or try --overlap=0 options."
            )
            exit(1)

        self.width: float = width
        self.height: float = height
        self.overlap: int = overlap

    def check(self, point: np.ndarray) -> bool:
        """Check whether point is already occupied by other elements."""
        if 0.0 <= point[0] < self.width and 0.0 <= point[1] < self.height:
            return self.matrix[point[0], point[1]]
        return True

    def register(self, point: np.ndarray) -> None:
        """Register that point is occupied by an element."""
        if 0.0 <= point[0] < self.width and 0.0 <= point[1] < self.height:
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
        point: np.ndarray,
        priority: float = 0.0,
        is_for_node: bool = True,
        draw_outline: bool = True,
        add_tooltips: bool = False,
    ) -> None:
        super().__init__(tags)

        assert point is not None

        self.icon_set: IconSet = icon_set
        self.labels: list[Label] = labels
        self.processed: set[str] = processed
        self.point: np.ndarray = point
        self.priority: float = priority
        self.layer: float = 0.0
        self.is_for_node: bool = is_for_node
        self.draw_outline: bool = draw_outline
        self.add_tooltips: bool = add_tooltips

        self.y: float = 0.0
        self.main_icon_painted: bool = False

    def draw_main_shapes(
        self, svg: svgwrite.Drawing, occupied: Optional[Occupied] = None
    ) -> None:

        """Draw main shape for one node."""
        keys_left = [x for x in self.tags.keys() if x not in self.processed]
        if (
            self.icon_set.main_icon.is_default()
            and not self.icon_set.extra_icons
            and (not keys_left or not self.is_for_node)
        ):
            return

        if self.icon_set.main_icon.is_default(): # Draw only custom icons
            return

        position: np.ndarray = self.point + np.array((0.0, self.y))
        tags: Optional[dict[str, str]] = (
            self.tags if self.add_tooltips else None
        )
        self.main_icon_painted: bool = self.draw_point_shape(
            svg,
            self.icon_set.main_icon,
            self.icon_set.default_icon,
            position,
            occupied,
            tags=tags,
        )
        if self.main_icon_painted:
            self.y += 16.0

    def draw_extra_shapes(
        self, svg: svgwrite.Drawing, occupied: Optional[Occupied] = None
    ) -> None:
        """Draw secondary shapes."""
        if not self.icon_set.extra_icons or not self.main_icon_painted:
            return

        is_place_for_extra: bool = True
        if occupied:
            left: float = -(len(self.icon_set.extra_icons) - 1.0) * 8.0
            for _ in self.icon_set.extra_icons:
                point: np.ndarray = np.array(
                    (int(self.point[0] + left), int(self.point[1] + self.y))
                )
                if occupied.check(point):
                    is_place_for_extra = False
                    break
                left += 16.0

        if is_place_for_extra:
            left: float = -(len(self.icon_set.extra_icons) - 1.0) * 8.0
            for icon in self.icon_set.extra_icons:
                point: np.ndarray = self.point + np.array((left, self.y))
                self.draw_point_shape(svg, icon, None, point, occupied=occupied)
                left += 16.0
            if self.icon_set.extra_icons:
                self.y += 16.0

    def draw_point_shape(
        self,
        svg: svgwrite.Drawing,
        icon: Icon,
        default_icon: Optional[Icon],
        position: np.ndarray,
        occupied: Optional[Occupied],
        tags: Optional[dict[str, str]] = None,
    ) -> bool:
        """Draw one combined icon and its outline."""
        # Down-cast floats to integers to make icons pixel-perfect.
        position: np.ndarray = np.array((int(position[0]), int(position[1])))

        icon_to_draw: Icon = icon
        is_painted: bool = True

        if occupied and occupied.check(position):
            if default_icon:
                icon_to_draw = default_icon
                is_painted = False
            else:
                return False

        if self.draw_outline:
            icon_to_draw.draw(svg, position, outline=True)

        icon_to_draw.draw(svg, position, tags=tags)

        if occupied and is_painted:
            overlap: int = occupied.overlap
            for i in range(-overlap, overlap):
                for j in range(-overlap, overlap):
                    occupied.register(
                        np.array((position[0] + i, position[1] + j))
                    )

        return is_painted

    def draw_texts(
        self,
        svg: svgwrite.Drawing,
        occupied: Optional[Occupied] = None,
        label_mode: LabelMode = LabelMode.MAIN,
    ) -> None:
        """Draw all labels."""
        labels: list[Label]

        if label_mode == LabelMode.MAIN:
            labels = self.labels[:1]
        elif label_mode == LabelMode.ALL:
            labels = self.labels
        else:
            return

        for label in labels:
            text = label.text
            text = text.replace("&quot;", '"')
            text = text.replace("&amp;", "&")
            text = text[:26] + ("..." if len(text) > 26 else "")
            point = self.point + np.array((0.0, self.y + 2.0))
            self.draw_text(
                svg,
                text,
                point,
                occupied,
                label.fill,
                label.size,
                label.out_fill,
            )

    def draw_text(
        self,
        svg: svgwrite.Drawing,
        text: str,
        point: np.ndarray,
        occupied: Optional[Occupied],
        fill: Color,
        size: float,
        out_fill: Color,
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
        length: int = len(text) * 6  # FIXME

        if occupied:
            is_occupied: bool = False
            for i in range(-int(length / 2.0), int(length / 2.0)):
                text_position: np.ndarray = np.array(
                    (int(point[0] + i), int(point[1] - 4.0))
                )
                if occupied.check(text_position):
                    is_occupied = True
                    break

            if is_occupied:
                return

            for i in range(-int(length / 2.0), int(length / 2.0)):
                for j in range(-12, 5):
                    occupied.register(
                        np.array((int(point[0] + i), int(point[1] + j)))
                    )
                    if is_debug:
                        svg.add(svg.rect((point[0] + i, point[1] + j), (1, 1)))

        if out_fill_2:
            draw_text(
                svg,
                text,
                point,
                size,
                fill=out_fill_2,
                stroke_width=5.0,
                stroke=out_fill_2,
                opacity=out_opacity_2,
            )
        if out_fill:
            draw_text(
                svg,
                text,
                point,
                size,
                fill,
                stroke_width=3.0,
                stroke=out_fill,
                opacity=out_opacity,
            )
        draw_text(svg, text, point, size, fill)

        self.y += 11

    def get_size(self) -> np.ndarray:
        """
        Get width and height of the point visual representation if there is
        space for all elements.
        """
        icon_size: int = 16
        width: int = icon_size * (
            1 + max(2, len(self.icon_set.extra_icons) - 1)
        )
        height: int = icon_size * (
            1 + np.ceil(len(self.icon_set.extra_icons) / 3.0)
        )
        if len(self.labels):
            height += 4 + 11 * len(self.labels)
        return np.array((width, height))
