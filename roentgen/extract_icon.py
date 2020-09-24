"""
Extract icons from SVG file.

Author: Sergey Vartanov (me@enzet.ru).
"""
import re
import xml.dom.minidom
from typing import Dict
from xml.dom.minidom import Element, Node

import numpy as np
from svgwrite import Drawing

from roentgen import ui

DEFAULT_SHAPE_ID: str = "default"
DEFAULT_SMALL_SHAPE_ID: str = "default_small"
STANDARD_INKSCAPE_ID: str = "(path|rect)\\d*"

GRID_STEP: int = 16


class Icon:
    """
    SVG icon path description.
    """
    def __init__(self, path: str, offset: np.array, id_: str):
        """
        :param path: SVG icon path
        :param offset: vector that should be used to shift the path
        :param id_: shape identifier
        """
        assert path

        self.path: str = path
        self.offset: np.array = offset
        self.id_: str = id_

    def is_default(self) -> bool:
        """
        Return true if icon is has a default shape that doesn't represent
        anything.
        """
        return self.id_ in [DEFAULT_SHAPE_ID, DEFAULT_SMALL_SHAPE_ID]

    def get_path(self, svg: Drawing, point: np.array):
        """
        Draw icon into SVG file.

        :param svg: SVG file to draw to
        :param point: icon position
        """
        shift: np.array = self.offset + point

        return svg.path(
            d=self.path, transform=f"translate({shift[0]},{shift[1]})")


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
        self.icons: Dict[str, Icon] = {}

        with open(svg_file_name) as input_file:
            content = xml.dom.minidom.parse(input_file)
            for element in content.childNodes:
                if element.nodeName == "svg":
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

        if ("id" in node.attributes.keys() and
                "d" in node.attributes.keys() and
                node.attributes["id"].value):
            path: str = node.attributes["d"].value
            matcher = re.match("[Mm] ([0-9.e-]*)[, ]([0-9.e-]*)", path)
            if not matcher:
                ui.error(f"invalid path: {path}")
                return

            def get_offset(value: float):
                """ Get negated icon offset from the origin. """
                return -int(value / GRID_STEP) * GRID_STEP - GRID_STEP / 2

            point: np.array = np.array((
                get_offset(float(matcher.group(1))),
                get_offset(float(matcher.group(2)))))

            id_: str = node.attributes["id"].value
            matcher = re.match(STANDARD_INKSCAPE_ID, id_)
            if not matcher:
                self.icons[id_] = Icon(node.attributes["d"].value, point, id_)

    def get_path(self, id_: str) -> (Icon, bool):
        """
        Get SVG path of the icon.

        :param id_: string icon identifier
        """
        if id_ in self.icons:
            return self.icons[id_], True

        ui.error(f"no such icon ID {id_}")
        return self.icons[DEFAULT_SHAPE_ID], False
