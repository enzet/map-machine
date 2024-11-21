"""Extract icons from SVG file."""

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

import numpy as np
import svgwrite
from colour import Color
from svgwrite import Drawing
from svgwrite.base import BaseElement
from svgwrite.container import Group
from svgwrite.path import Path as SVGPath

from map_machine.color import is_bright

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

DEFAULT_SHAPE_ID: str = "default"
DEFAULT_SMALL_SHAPE_ID: str = "default_small"

STANDARD_INKSCAPE_ID_MATCHER: re.Pattern = re.compile(
    "^((circle|defs|ellipse|grid|guide|marker|metadata|path|rect|use)"
    "[\\d-]+|base)$"
)
PATH_MATCHER: re.Pattern = re.compile("[Mm] ([0-9.e-]*)[, ]([0-9.e-]*)")

GRID_STEP: int = 16

USED_ICON_COLOR: str = "#000000"
UNUSED_ICON_COLORS: list[str] = ["#0000ff", "#ff0000"]


@dataclass
class Shape:
    """SVG icon path description."""

    # String representation of SVG path commands.
    path: str

    # Vector that should be used to shift the path.
    offset: np.ndarray

    # Shape unique string identifier, e.g. `tree`.
    id_: str

    # Shape human-readable description.
    name: Optional[str] = None

    # If value is `None`, shape doesn't have distinct direction or its
    # direction doesn't make sense.  Shape is directed to the right if value is
    # `True` and to the left if value is `False`.
    #
    # E.g. CCTV camera shape has direction and may be flipped horizontally to
    # follow surveillance direction, whereas car shape has direction but
    # flipping icon doesn't make any sense.
    is_right_directed: Optional[bool] = None

    # Set of emojis that represent the same entity.  E.g. 🍐 (pear) for `pear`;
    # 🍏 (green apple) and 🍎 (red apple) for `apple`.
    emojis: set[str] = field(default_factory=set)

    # If shape is used only as a part of other icons.
    is_part: bool = False

    # Hierarchical icon group.  Is used for icon sorting.
    group: str = ""

    # Icon categories that is used in OpenStreetMap wiki.  E.g. `barrier` means
    # https://wiki.openstreetmap.org/wiki/Category:Barrier_icons.
    categories: set[str] = field(default_factory=set)

    @classmethod
    def from_structure(
        cls,
        structure: dict[str, Any],
        path: str,
        offset: np.ndarray,
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
        shape: "Shape" = cls(path, offset, id_, name)

        if "name" in structure:
            shape.name = structure["name"]

        if "directed" in structure:
            if structure["directed"] == "right":
                shape.is_right_directed = True
            if structure["directed"] == "left":
                shape.is_right_directed = False

        if "emoji" in structure:
            emojis = structure["emoji"]
            shape.emojis = [emojis] if isinstance(emojis, str) else emojis

        shape.is_part = structure.get("is_part", False)
        shape.group = structure.get("group", "")

        if "categories" in structure:
            shape.categories = set(structure["categories"])

        return shape

    def is_default(self) -> bool:
        """
        Return true if icon is has a default shape that doesn't represent
        anything.
        """
        return self.id_ in [DEFAULT_SHAPE_ID, DEFAULT_SMALL_SHAPE_ID]

    def get_path(
        self,
        point: np.ndarray,
        offset: np.ndarray = np.array((0.0, 0.0)),
        scale: np.ndarray = np.array((1.0, 1.0)),
    ) -> SVGPath:
        """
        Draw icon into SVG file.

        :param point: icon position
        :param offset: additional offset
        :param scale: scale resulting image
        """
        transformations: list[str] = []
        shift: np.ndarray = point + offset

        transformations.append(f"translate({shift[0]},{shift[1]})")

        if not np.allclose(scale, np.array((1.0, 1.0))):
            transformations.append(f"scale({scale[0]},{scale[1]})")

        transformations.append(f"translate({self.offset[0]},{self.offset[1]})")

        return svgwrite.path.Path(
            d=self.path, transform=" ".join(transformations)
        )

    def get_full_id(self) -> str:
        """Compute full shape identifier with group for sorting."""
        return self.group + "_" + self.id_


def parse_length(text: str) -> float:
    """Parse length from SVG attribute."""
    if text.endswith("px"):
        text = text[:-2]
    return float(text)


def verify_sketch_element(element: Element, id_: str) -> bool:
    """
    Verify sketch SVG element from icon file.

    :param element: sketch SVG element (element with standard Inkscape
        identifier)
    :param id_: element `id` attribute
    :return: True iff SVG element has valid style
    """
    if "style" not in element.attrib or not element.attrib["style"]:
        return True

    style: dict[str, str] = dict(
        (x.split(":")[0], x.split(":")[1])
        for x in element.attrib["style"].split(";")
    )

    # Sketch element (black 0.1 px stroke, no fill).

    if (
        style["fill"] == "none"
        and style["stroke"] == "#000000"
        and "stroke-width" in style
        and np.allclose(parse_length(style["stroke-width"]), 0.1)
    ):
        return True

    # Sketch element (black 1 px stroke, no fill, 20% opacity).

    if (
        style["fill"] == "none"
        and style["stroke"] == "#000000"
        and "opacity" in style
        and np.allclose(float(style["opacity"]), 0.2)
        and (
            "stroke-width" not in style
            or np.allclose(parse_length(style["stroke-width"]), 0.7)
            or np.allclose(parse_length(style["stroke-width"]), 1)
            or np.allclose(parse_length(style["stroke-width"]), 2)
            or np.allclose(parse_length(style["stroke-width"]), 3)
        )
    ):
        return True

    # Experimental shape (blue or red fill, no stroke).

    if (
        style["fill"] in UNUSED_ICON_COLORS
        and "stroke" in style
        and style["stroke"] == "none"
    ):
        return True

    if style and not id_.startswith("use"):
        return False

    return True


def parse_configuration(root: dict, configuration: dict, group: str) -> None:
    """
    Shape description is a probably empty dictionary with optional fields
    `name`, `emoji`, `is_part`, `directed`, and `categories`.  Shape
    configuration is a dictionary that contains shape descriptions.  Shape
    descriptions may be grouped and the nesting level may be arbitrary:

    {
        <shape id>: {<shape description>},
        <shape id>: {<shape description>},
        <group>: {
            <shape id>: {<shape description>},
            <shape id>: {<shape description>}
        },
        <group>: {
            <subgroup>: {
                <shape id>: {<shape description>},
                <shape id>: {<shape description>}
            }
        }
    }
    """
    for key, value in root.items():
        if (
            not value
            or "name" in value
            or "emoji" in value
            or "is_part" in value
            or "directed" in value
            or "categories" in value
        ):
            configuration[key] = value | {"group": group}
        else:
            parse_configuration(value, configuration, f"{group}_{key}")


class ShapeExtractor:
    """
    Extract shapes from SVG file.

    Shape is a single path with "id" attribute that aligned to 16×16 grid.
    """

    def __init__(
        self, svg_file_name: Path, configuration_file_name: Path
    ) -> None:
        """
        :param svg_file_name: input SVG file name with icons.  File may contain
            any other irrelevant graphics.
        :param configuration_file_name: JSON file with grouped shape
            descriptions
        """
        self.shapes: dict[str, Shape] = {}

        self.configuration: dict[str, Any] = {}
        parse_configuration(
            json.load(configuration_file_name.open(encoding="utf-8")),
            self.configuration,
            "root",
        )
        root: Element = ElementTree.parse(svg_file_name).getroot()
        self.parse(root)

        for shape_id in self.configuration:
            if shape_id not in self.shapes:
                logging.warning(
                    f"Configuration for unknown shape `{shape_id}`."
                )

    def parse(self, node: Element) -> None:
        """
        Extract icon paths into a map.

        :param node: XML node that contains icon
        """
        if node.tag.endswith("}g") or node.tag.endswith("}svg"):
            for sub_node in node:
                self.parse(sub_node)
            return

        if "id" not in node.attrib or not node.attrib["id"]:
            return

        id_: str = node.attrib["id"]
        if STANDARD_INKSCAPE_ID_MATCHER.match(id_) is not None:
            if not verify_sketch_element(node, id_):
                path_part = ""
                try:
                    path_part = f", {node.attrib['d'].split(' ')[:3]}."
                except (KeyError, ValueError):
                    pass
                logging.warning(f"Not verified SVG element `{id_}`{path_part}")
            return

        if "d" in node.attrib and node.attrib["d"]:
            path: str = node.attrib["d"]
            matcher = PATH_MATCHER.match(path)
            if not matcher:
                return

            name: Optional[str] = None

            def get_offset(value: str) -> float:
                """Get negated icon offset from the origin."""
                return (
                    -int(float(value) / GRID_STEP) * GRID_STEP - GRID_STEP / 2.0
                )

            point: np.ndarray = np.array(
                (get_offset(matcher.group(1)), get_offset(matcher.group(2)))
            )
            for child_node in node:
                if isinstance(child_node, Element):
                    name = child_node.text
                    break

            configuration: dict[str, Any] = {}

            if id_ in self.configuration:
                configuration = self.configuration[id_]
                if "name" not in configuration:
                    logging.warning(f"Shape `{id_}` doesn't have name.")
            else:
                logging.warning(f"Shape `{id_}` doesn't have configuration.")

            self.shapes[id_] = Shape.from_structure(
                configuration, path, point, id_, name
            )
        else:
            logging.error(f"Not standard ID {id_}.")

    def get_shape(self, id_: str) -> Shape:
        """
        Get shape or None if there is no shape with such identifier.

        :param id_: string icon identifier
        """
        if id_ in self.shapes:
            return self.shapes[id_]

        assert False, f"no shape with id {id_} in icons file"


@dataclass
class ShapeSpecification:
    """Specification for shape as a part of an icon."""

    shape: Shape
    color: Color
    offset: np.ndarray = field(default_factory=lambda: np.array((0.0, 0.0)))
    flip_horizontally: bool = False
    flip_vertically: bool = False
    use_outline: bool = True

    def is_default(self) -> bool:
        """Check whether shape is default."""
        return self.shape.id_ == DEFAULT_SHAPE_ID

    def draw(
        self,
        svg: BaseElement,
        point: np.ndarray,
        tags: dict[str, Any] = None,
        outline: bool = False,
        outline_opacity: float = 1.0,
        scale: float = 1.0,
    ) -> None:
        """
        Draw icon shape into SVG file.

        :param svg: output SVG file
        :param point: 2D position of the shape centre
        :param tags: tags to be displayed as a tooltip, if tooltip should not be
            displayed, this argument should be None
        :param outline: draw outline for the shape
        :param outline_opacity: opacity of the outline
        :param scale: scale icon by the magnitude
        """
        scale_vector: np.ndarray = np.array((scale, scale))
        if self.flip_vertically:
            scale_vector = np.array((scale, -scale))
        if self.flip_horizontally:
            scale_vector = np.array((-scale, scale))

        point: np.ndarray = np.array(list(map(int, point)))
        path: SVGPath = self.shape.get_path(
            point, self.offset * scale, scale_vector
        )
        path.update({"fill": self.color.hex})

        if outline and self.use_outline:
            bright: bool = is_bright(self.color)
            color: Color = Color("black") if bright else Color("white")

            style: dict[str, Any] = {
                "fill": color.hex,
                "stroke": color.hex,
                "stroke-width": 2.2,
                "stroke-linejoin": "round",
                "opacity": outline_opacity,
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

    def __lt__(self, other: "ShapeSpecification") -> bool:
        return self.shape.id_ < other.shape.id_


@dataclass
class Icon:
    """Icon that consists of (probably) multiple shapes."""

    shape_specifications: list[ShapeSpecification]
    opacity: float = 1.0

    def get_shape_ids(self) -> list[str]:
        """Get all shape identifiers in the icon."""
        return [x.shape.id_ for x in self.shape_specifications]

    def has_names(self) -> bool:
        """Check whether oll shape names are known."""
        for specification in self.shape_specifications:
            if not specification.shape.name:
                return False

        return True

    def get_names(self) -> list[str]:
        """Get all shape names in the icon."""
        return [
            (x.shape.name if x.shape.name else "unknown")
            for x in self.shape_specifications
        ]

    def get_name(self) -> str:
        """Get combined human-readable icon name."""
        names: list[str] = self.get_names()

        if len(names) == 1:
            return names[0]

        return ", ".join(names[:-1]) + " and " + names[-1]

    def has_categories(self) -> bool:
        """Check whether oll shape categories are known."""
        for specification in self.shape_specifications:
            if specification.shape.categories:
                return True

        return False

    def get_categories(self) -> set[str]:
        """Get all shape names in the icon."""
        result: set[str] = set()

        for specification in self.shape_specifications:
            result = result.union(specification.shape.categories)

        return result

    def draw(
        self,
        svg: svgwrite.Drawing,
        point: np.ndarray,
        tags: dict[str, Any] = None,
        outline: bool = False,
        scale: float = 1.0,
    ) -> None:
        """
        Draw icon to SVG.

        :param svg: output SVG file
        :param point: 2D position of the icon centre
        :param tags: tags to be displayed as a tooltip
        :param outline: draw outline for the icon
        :param scale: scale icon by the magnitude
        """
        if outline:
            bright: bool = is_bright(self.shape_specifications[0].color)
            opacity: float = 0.7 if bright else 0.5
            outline_group: Group = Group(opacity=opacity)
            for shape_specification in self.shape_specifications:
                shape_specification.draw(
                    outline_group, point, tags, True, scale=scale
                )
            svg.add(outline_group)
        else:
            group: Group = Group(opacity=self.opacity)
            for shape_specification in self.shape_specifications:
                shape_specification.draw(group, point, tags, scale=scale)
            svg.add(group)

    def draw_to_file(
        self,
        file_name: Path,
        color: Optional[Color] = None,
        outline: bool = False,
        outline_opacity: float = 1.0,
    ) -> None:
        """
        Draw icon to the SVG file.

        :param file_name: output SVG file name
        :param color: fill color
        :param outline: if true, draw outline beneath the icon
        :param outline_opacity: opacity of the outline
        """
        svg: Drawing = Drawing(str(file_name), (16, 16))

        if outline:
            for shape_specification in self.shape_specifications:
                if color:
                    shape_specification.color = color
                shape_specification.draw(
                    svg,
                    np.array((8.0, 8.0)),
                    outline=outline,
                    outline_opacity=outline_opacity,
                )

        for shape_specification in self.shape_specifications:
            if color:
                shape_specification.color = color
            shape_specification.draw(svg, np.array((8.0, 8.0)))

        with file_name.open("w", encoding="utf-8") as output_file:
            svg.write(output_file)

    def is_default(self) -> bool:
        """Check whether first shape is default."""
        return (
            len(self.shape_specifications) == 1
            and self.shape_specifications[0].is_default()
        )

    def recolor(self, color: Color, white: Optional[Color] = None) -> None:
        """Paint all shapes in the color."""
        for shape_specification in self.shape_specifications:
            if shape_specification.color == Color("white") and white:
                shape_specification.color = white
            else:
                shape_specification.color = color

    def add_specifications(
        self, specifications: list[ShapeSpecification]
    ) -> None:
        """Add shape specifications to the icon."""
        self.shape_specifications += specifications

    def __eq__(self, other: "Icon") -> bool:
        return sorted(self.shape_specifications) == sorted(
            other.shape_specifications
        )

    def __lt__(self, other: "Icon") -> bool:
        return "".join(
            [x.shape.get_full_id() for x in self.shape_specifications]
        ) < "".join([x.shape.get_full_id() for x in other.shape_specifications])


@dataclass
class IconSet:
    """Node representation: icons and color."""

    main_icon: Icon
    extra_icons: list[Icon]

    # Icon to use if the point is hidden by overlapped icons but still need to
    # be shown.
    default_icon: Optional[Icon]

    # Tag keys that were processed to create icon set (other tag keys should be
    # displayed by text or ignored)
    processed: set[str]
