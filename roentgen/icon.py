"""
Extract icons from SVG file.
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from xml.dom.minidom import Document, Element, Node, parse

import numpy as np
import svgwrite
from colour import Color
from svgwrite import Drawing
from svgwrite.path import Path as SvgPath

from roentgen.color import is_bright
from roentgen.ui import error

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

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
    is_right_directed: Optional[bool] = None
    emojis: Set[str] = field(default_factory=set)
    is_part: bool = False

    @classmethod
    def from_structure(
        cls,
        structure: Dict[str, Any],
        path: str,
        offset: np.array,
        id_: str,
        name: Optional[str] = None,
    ) -> "Shape":
        """
        Parse shape description from structure.

        :param structure: input structure
        :param path: SVG path commands in string form
        :param offset: shape offset in the input file
        :param id_: shape unique identifier
        :param name: shape text description
        """
        shape = cls(path, offset, id_, name)

        if "directed" in structure:
            if structure["directed"] == "right":
                shape.is_right_directed = True
            if structure["directed"] == "left":
                shape.is_right_directed = False

        if "emoji" in structure:
            emojis = structure["emoji"]
            shape.emojis = [emojis] if isinstance(emojis, str) else emojis

        if "is_part" in structure:
            shape.is_part = structure["is_part"]

        return shape

    def is_default(self) -> bool:
        """
        Return true if icon is has a default shape that doesn't represent
        anything.
        """
        return self.id_ in [DEFAULT_SHAPE_ID, DEFAULT_SMALL_SHAPE_ID]

    def get_path(
        self,
        svg: Drawing,
        point: np.array,
        offset: np.array = np.array((0, 0)),
        scale: np.array = np.array((1, 1)),
    ) -> SvgPath:
        """
        Draw icon into SVG file.

        :param svg: SVG file to draw to
        :param point: icon position
        :param offset: additional offset
        :param scale: scale resulting image
        """
        transformations: List[str] = []
        shift: np.array = point + offset

        transformations.append(f"translate({shift[0]},{shift[1]})")

        if not np.allclose(scale, np.array((1, 1))):
            transformations.append(f"scale({scale[0]},{scale[1]})")

        transformations.append(f"translate({self.offset[0]},{self.offset[1]})")

        return svg.path(d=self.path, transform=" ".join(transformations))


class ShapeExtractor:
    """
    Extract shapes from SVG file.

    Shape is a single path with "id" attribute that aligned to 16×16 grid.
    """

    def __init__(self, svg_file_name: Path, configuration_file_name: Path):
        """
        :param svg_file_name: input SVG file name with icons.  File may contain
            any other irrelevant graphics.
        """
        self.shapes: Dict[str, Shape] = {}
        self.configuration: Dict[str, Any] = json.load(
            configuration_file_name.open()
        )
        with svg_file_name.open() as input_file:
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

            def get_offset(value: str):
                """Get negated icon offset from the origin."""
                return (
                    -int(float(value) / GRID_STEP) * GRID_STEP - GRID_STEP / 2
                )

            point: np.array = np.array(
                (get_offset(matcher.group(1)), get_offset(matcher.group(2)))
            )
            for child_node in node.childNodes:
                if isinstance(child_node, Element):
                    name = child_node.childNodes[0].nodeValue
                    break

            configuration: Dict[str, Any] = (
                self.configuration[id_] if id_ in self.configuration else {}
            )
            self.shapes[id_] = Shape.from_structure(
                configuration, path, point, id_, name
            )
        else:
            error(f"not standard ID {id_}")

    def get_shape(self, id_: str) -> Optional[Shape]:
        """
        Get shape or None if there is no shape with such identifier.

        :param id_: string icon identifier
        """
        if id_ in self.shapes:
            return self.shapes[id_]

        assert False, f"no shape with id {id_} in icons file"


@dataclass
class ShapeSpecification:
    """
    Specification for shape as a part of an icon.
    """

    shape: Shape
    color: Color = DEFAULT_COLOR
    offset: np.array = np.array((0, 0))
    flip_horizontally: bool = False
    flip_vertically: bool = False
    use_outline: bool = True

    @classmethod
    def from_structure(
        cls,
        structure: Any,
        extractor: ShapeExtractor,
        scheme,
        color: Color = DEFAULT_COLOR,
    ) -> "ShapeSpecification":
        """
        Parse shape specification from structure, that is just shape string
        identifier or dictionary with keys: shape (required), color (optional),
        and offset (optional).
        """
        shape: Shape = extractor.get_shape(DEFAULT_SHAPE_ID)
        color: Color = color
        offset: np.array = np.array((0, 0))
        flip_horizontally: bool = False
        flip_vertically: bool = False
        use_outline: bool = True

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
            if "flip_horizontally" in structure:
                flip_horizontally = structure["flip_horizontally"]
            if "flip_vertically" in structure:
                flip_vertically = structure["flip_vertically"]
            if "outline" in structure:
                use_outline = structure["outline"]

        return cls(
            shape, color, offset, flip_horizontally, flip_vertically,
            use_outline
        )

    def is_default(self) -> bool:
        """
        Check whether shape is default.
        """
        return self.shape.id_ == DEFAULT_SHAPE_ID

    def draw(
        self,
        svg: svgwrite.Drawing,
        point: np.array,
        tags: Dict[str, Any] = None,
        outline: bool = False,
    ) -> None:
        """
        Draw icon shape into SVG file.

        :param svg: output SVG file
        :param point: 2D position of the shape centre
        :param tags: tags to be displayed as hint
        :param outline: draw outline for the shape
        """
        scale: np.array = np.array((1, 1))
        if self.flip_vertically:
            scale = np.array((1, -1))
        if self.flip_horizontally:
            scale = np.array((-1, 1))

        point = np.array(list(map(int, point)))
        path = self.shape.get_path(svg, point, self.offset, scale)
        path.update({"fill": self.color.hex})

        if outline and self.use_outline:
            bright: bool = is_bright(self.color)
            color: Color = Color("black") if bright else Color("white")
            opacity: float = 0.7 if bright else 0.5

            style: Dict[str, Any] = {
                "fill": color.hex,
                "stroke": color.hex,
                "stroke-width": 2.2,
                "stroke-linejoin": "round",
                "opacity": opacity,
            }
            path.update(style)
        if tags:
            title: str = "\n".join(map(lambda x: x + ": " + tags[x], tags))
            path.set_desc(title=title)

        svg.add(path)

    def __eq__(self, other: "ShapeSpecification") -> bool:
        return (
            self.shape == other.shape
            and self.color == other.color
            and np.allclose(self.offset, other.offset)
        )

    def __lt__(self, other) -> bool:
        return self.shape.id_ < other.shape.id_


@dataclass
class Icon:
    """
    Icon that consists of (probably) multiple shapes.
    """

    shape_specifications: List[ShapeSpecification]

    def get_shape_ids(self) -> List[str]:
        """
        Get all shape identifiers in the icon.
        """
        return [x.shape.id_ for x in self.shape_specifications]

    def get_names(self) -> List[str]:
        """
        Gat all shape names in the icon.
        """
        return [
            (x.shape.name if x.shape.name else "unknown")
            for x in self.shape_specifications
        ]

    def draw(
        self,
        svg: svgwrite.Drawing,
        point: np.array,
        tags: Dict[str, Any] = None,
        outline: bool = False,
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

    def draw_to_file(self, file_name: Path):
        """
        Draw icon to the SVG file.

        :param file_name: output SVG file name
        """
        svg: Drawing = Drawing(str(file_name), (16, 16))

        for shape_specification in self.shape_specifications:
            shape_specification.draw(svg, (8, 8))

        with file_name.open("w") as output_file:
            svg.write(output_file)

    def is_default(self) -> bool:
        """
        Check whether first shape is default.
        """
        return self.shape_specifications[0].is_default()

    def recolor(self, color: Color, white: Optional[Color] = None) -> None:
        """
        Paint all shapes in the color.
        """
        for shape_specification in self.shape_specifications:
            if shape_specification.color == Color("white") and white:
                shape_specification.color = white
            else:
                shape_specification.color = color

    def add_specifications(
        self, specifications: List[ShapeSpecification]
    ) -> None:
        """
        Add shape specifications to the icon.
        """
        self.shape_specifications += specifications

    def __eq__(self, other) -> bool:
        return sorted(self.shape_specifications) == sorted(
            other.shape_specifications
        )

    def __lt__(self, other) -> bool:
        return (
            "".join([x.shape.id_ for x in self.shape_specifications])
            < "".join([x.shape.id_ for x in other.shape_specifications])
        )


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
