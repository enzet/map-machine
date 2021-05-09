"""
Extract icons from SVG file.

Author: Sergey Vartanov (me@enzet.ru).
"""
import re
from dataclasses import dataclass
from typing import Dict, Optional
from xml.dom.minidom import Document, Element, Node, parse

import numpy as np
from svgwrite import Drawing

from roentgen import ui

DEFAULT_SHAPE_ID: str = "default"
DEFAULT_SMALL_SHAPE_ID: str = "default_small"
STANDARD_INKSCAPE_ID: str = (
    "^((circle|defs|ellipse|metadata|path|rect|use)[\\d-]+|base)$"
)

GRID_STEP: int = 16


@dataclass
class Shape:
    """
    SVG icon path description.
    """

    path: str  # SVG icon path
    offset: np.array  # vector that should be used to shift the path
    id_: str  # shape identifier
    name: Optional[str] = None  # icon description

    def is_default(self) -> bool:
        """
        Return true if icon is has a default shape that doesn't represent
        anything.
        """
        return self.id_ in [DEFAULT_SHAPE_ID, DEFAULT_SMALL_SHAPE_ID]

    def get_path(
        self, svg: Drawing, point: np.array, offset: np.array = np.array((0, 0))
    ):
        """
        Draw icon into SVG file.

        :param svg: SVG file to draw to
        :param point: icon position
        :param offset: additional offset
        """
        shift: np.array = self.offset + point + offset

        return svg.path(
            d=self.path, transform=f"translate({shift[0]},{shift[1]})"
        )


class IconExtractor:
    """
    Extract icons from SVG file.

    Icon is a single path with "id" attribute that aligned to 16×16 grid.
    """

    def __init__(self, svg_file_name: str):
        """
        :param svg_file_name: input SVG file name with icons.  File may contain
            any other irrelevant graphics.
        """
        self.shapes: Dict[str, Shape] = {}

        with open(svg_file_name) as input_file:
            content: Document = parse(input_file)
            for element in content.childNodes:  # type: Element
                if element.nodeName != "svg":
                    continue
                for node in element.childNodes:  # type: Node
                    if isinstance(node, Element):
                        self.parse(node)

    def parse(self, node: Element) -> None:
        """
        Extract icon paths into a map.

        :param node: XML node that contains icon
        """
        if node.nodeName == "g":
            for sub_node in node.childNodes:
                if isinstance(sub_node, Element):
                    self.parse(sub_node)
            return

        if not node.hasAttribute("id") or not node.getAttribute("id"):
            return

        id_: str = node.getAttribute("id")
        if re.match(STANDARD_INKSCAPE_ID, id_) is not None:
            return

        if node.hasAttribute("d"):
            path: str = node.getAttribute("d")
            matcher = re.match("[Mm] ([0-9.e-]*)[, ]([0-9.e-]*)", path)
            if not matcher:
                return

            name: Optional[str] = None

            def get_offset(value: float):
                """
                Get negated icon offset from the origin.
                """
                return -int(value / GRID_STEP) * GRID_STEP - GRID_STEP / 2

            point: np.array = np.array((
                get_offset(float(matcher.group(1))),
                get_offset(float(matcher.group(2))),
            ))

            for child_node in node.childNodes:
                if isinstance(child_node, Element):
                    name = child_node.childNodes[0].nodeValue
                    break

            self.shapes[id_] = Shape(path, point, id_, name)
        else:
            ui.error(f"not standard ID {id_}")

    def get_path(self, id_: str) -> (Shape, bool):
        """
        Get SVG path of the icon.

        :param id_: string icon identifier
        """
        if id_ in self.shapes:
            return self.shapes[id_], True

        ui.error(f"no such shape ID {id_}")
        return self.shapes[DEFAULT_SHAPE_ID], False
