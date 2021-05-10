"""
Extract icons from SVG file.

Author: Sergey Vartanov (me@enzet.ru).
"""
import re
from dataclasses import dataclass
from typing import Dict, Optional, List, Set, Any
from xml.dom.minidom import Document, Element, Node, parse

import numpy as np
import svgwrite
from colour import Color
from svgwrite import Drawing

from roentgen.color import is_bright
from roentgen.ui import error

DEFAULT_COLOR: Color = Color("#444444")
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


class ShapeExtractor:
    """
    Extract shapes from SVG file.

    Shape is a single path with "id" attribute that aligned to 16×16 grid.
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
            error(f"not standard ID {id_}")

    def get_shape(self, id_: str) -> Optional[Shape]:
        """
        Get shape or None if there is no shape with such identifier.

        :param id_: string icon identifier
        """
        if id_ in self.shapes:
            return self.shapes[id_]


@dataclass
class ShapeSpecification:
    """
    Specification for shape as a part of an icon.
    """

    shape: Shape
    color: Color = DEFAULT_COLOR
    offset: np.array = np.array((0, 0))

    @classmethod
    def from_structure(
        cls, structure: Any, extractor: ShapeExtractor, scheme: "Scheme",
        color: Color = DEFAULT_COLOR
    ) -> "ShapeSpecification":
        """
        Parse shape specification from structure, that is just shape string
        identifier or dictionary with keys: shape (required), color (optional),
        and offset (optional).
        """
        shape: Shape = extractor.get_shape(DEFAULT_SHAPE_ID)
        color: Color = color
        offset: np.array = np.array((0, 0))

        if isinstance(structure, str):
            shape = extractor.get_shape(structure)
        elif isinstance(structure, dict):
            if "shape" in structure:
                shape = extractor.get_shape(structure["shape"])
            else:
                error("invalid shape specification: 'shape' key expected")
            if "color" in structure:
                color = scheme.get_color(structure["color"])
            if "offset" in structure:
                offset = np.array(structure["offset"])

        return cls(shape, color, offset)

    def is_default(self) -> bool:
        """
        Check whether shape is default.
        """
        return self.shape.id_ == DEFAULT_SHAPE_ID

    def draw(
        self, svg: svgwrite.Drawing, point: np.array,
        tags: Dict[str, Any] = None, outline: bool = False
    ) -> None:
        """
        Draw icon shape into SVG file.

        :param svg: output SVG file
        :param point: 2D position of the shape centre
        :param tags: tags to be displayed as hint
        :param outline: draw outline for the shape
        """
        point = np.array(list(map(int, point)))
        path = self.shape.get_path(svg, point, self.offset)
        path.update({"fill": self.color.hex})

        if outline:
            bright: bool = is_bright(self.color)
            color: Color = Color("black") if bright else Color("white")
            opacity: float = 0.7 if bright else 0.5

            path.update({
                "fill": color.hex,
                "stroke": color.hex,
                "stroke-width": 2.2,
                "stroke-linejoin": "round",
                "opacity": opacity,
            })
        if tags:
            title: str = "\n".join(map(lambda x: x + ": " + tags[x], tags))
            path.set_desc(title=title)

        svg.add(path)

    def __eq__(self, other: "ShapeSpecification") -> bool:
        return (
            self.shape == other.shape and
            self.color == other.color and
            np.allclose(self.offset, other.offset)
        )


@dataclass
class Icon:
    """
    Icon that consists of (probably) multiple shapes.
    """
    shape_specifications: List[ShapeSpecification]

    def get_shape_ids(self) -> Set[str]:
        """
        Get all shape identifiers in the icon.
        """
        return set(x.shape.id_ for x in self.shape_specifications)

    def get_names(self) -> List[str]:
        """
        Gat all shape names in the icon.
        """
        return [
            (x.shape.name if x.shape.name else "unknown")
            for x in self.shape_specifications
        ]

    def draw(
        self, svg: svgwrite.Drawing, point: np.array,
        tags: Dict[str, Any] = None, outline: bool = False
    ) -> None:
        """
        Draw icon to SVG.

        :param svg: output SVG file
        :param point: 2D position of the icon centre
        :param tags: tags to be displayed as hint
        :param outline: draw outline for the icon
        """
        for shape_specification in self.shape_specifications:
            shape_specification.draw(svg, point, tags, outline)

    def draw_to_file(self, file_name: str):
        """
        Draw icon to the SVG file.

        :param file_name: output SVG file name
        """
        svg: Drawing = Drawing(file_name, (16, 16))

        for shape_specification in self.shape_specifications:
            shape_specification.draw(svg, (8, 8))

        with open(file_name, "w") as output_file:
            svg.write(output_file)

    def is_default(self) -> bool:
        """
        Check whether first shape is default.
        """
        return self.shape_specifications[0].is_default()

    def recolor(self, color: Color) -> None:
        """
        Paint all shapes in the color.
        """
        for shape_specification in self.shape_specifications:
            shape_specification.color = color

    def add_specifications(
        self, specifications: List[ShapeSpecification]
    ) -> None:
        """
        Add shape specifications to the icon.
        """
        self.shape_specifications += specifications


@dataclass
class IconSet:
    """
    Node representation: icons and color.
    """
    main_icon: Icon
    extra_icons: List[Icon]

    # Tag keys that were processed to create icon set (other tag keys should be
    # displayed by text or ignored)
    processed: Set[str]
