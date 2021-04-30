"""
Extract icons from SVG file.

Author: Sergey Vartanov (me@enzet.ru).
"""
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional
from xml.dom.minidom import Document, Element, Node, parse

import numpy as np
import svgwrite
from colour import Color
from svgwrite import Drawing

from roentgen import ui

DEFAULT_SHAPE_ID: str = "default"
DEFAULT_SMALL_SHAPE_ID: str = "default_small"
STANDARD_INKSCAPE_ID: str = "^(circle|path|rect)\\d*$"

GRID_STEP: int = 16


@dataclass
class Icon:
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

    def get_path(self, svg: Drawing, point: np.array):
        """
        Draw icon into SVG file.

        :param svg: SVG file to draw to
        :param point: icon position
        """
        shift: np.array = self.offset + point

        return svg.path(
            d=self.path, transform=f"translate({shift[0]},{shift[1]})")

    def draw(
            self, svg: svgwrite.Drawing, point: np.array, color: Color,
            opacity=1.0, tags: Dict[str, Any] = None, outline: bool = False):
        """
        Draw icon shape into SVG file.

        :param svg: output SVG file
        :param point: icon position
        :param color: fill color
        :param opacity: icon opacity
        :param tags: tags to be displayed as hint
        :param outline: draw outline for the icon
        """
        point = np.array(list(map(int, point)))

        path: svgwrite.path.Path = self.get_path(svg, point)
        path.update({"fill": color.hex})
        if outline:
            opacity: float = 0.5

            path.update({
                "fill": color.hex, "stroke": color.hex, "stroke-width": 2.2,
                "stroke-linejoin": "round"})
        if opacity != 1.0:
            path.update({"opacity": opacity})
        if tags:
            title: str = "\n".join(map(lambda x: x + ": " + tags[x], tags))
            path.set_desc(title=title)
        svg.add(path)


def is_standard(id_: str):
    """ Check whether SVG object ID is standard Inkscape ID. """
    if id_ == "base":
        return True
    for prefix in ["path", "circle", "rect", "defs", "use", "metadata"]:
        matcher = re.match(prefix + "\\d+", id_)
        if matcher:
            return True
    return False


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
            content = parse(input_file)  # type: Document
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
        if is_standard(id_):
            return

        if node.hasAttribute("d"):
            path: str = node.getAttribute("d")
            matcher = re.match("[Mm] ([0-9.e-]*)[, ]([0-9.e-]*)", path)
            if not matcher:
                return

            name: Optional[str] = None

            def get_offset(value: float):
                """ Get negated icon offset from the origin. """
                return -int(value / GRID_STEP) * GRID_STEP - GRID_STEP / 2

            point: np.array = np.array((
                get_offset(float(matcher.group(1))),
                get_offset(float(matcher.group(2)))))

            for child_node in node.childNodes:
                if isinstance(child_node, Element):
                    name = child_node.childNodes[0].nodeValue
                    break

            matcher = re.match(STANDARD_INKSCAPE_ID, id_)
            if not matcher:
                self.icons[id_] = Icon(path, point, id_, name)
        else:
            ui.error(f"not standard ID {id_}")

    def get_path(self, id_: str) -> (Icon, bool):
        """
        Get SVG path of the icon.

        :param id_: string icon identifier
        """
        if id_ in self.icons:
            return self.icons[id_], True

        ui.error(f"no such icon ID {id_}")
        return self.icons[DEFAULT_SHAPE_ID], False
