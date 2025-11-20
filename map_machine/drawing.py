"""Drawing utility."""
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

import numpy as np
import svgwrite
from colour import Color
from svgwrite.base import BaseElement
from svgwrite.path import Path as SVGPath
from svgwrite.shapes import Rect
from svgwrite.text import Text

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

PathCommands = List[Union[float, str, np.ndarray]]

DEFAULT_FONT: str = "Helvetica"


@dataclass
class Style:
    """Drawing element style."""

    fill: Optional[Color] = None
    stroke: Optional[Color] = None
    width: float = 1.0

    def update_svg_element(self, element: BaseElement) -> None:
        """Set style for SVG element."""
        if self.fill is not None:
            element.update({"fill": self.fill})
        else:
            element.update({"fill": "none"})
        if self.stroke is not None:
            element.update({"stroke": self.stroke, "stroke-width": self.width})


class Drawing:
    """Image."""

    def __init__(self, file_path: Path, width: int, height: int) -> None:
        self.file_path: Path = file_path
        self.width: int = width
        self.height: int = height

    def rectangle(
        self, point_1: np.ndarray, point_2: np.ndarray, style: Style
    ) -> None:
        """Draw rectangle."""
        raise NotImplementedError

    def line(self, points: List[np.ndarray], style: Style) -> None:
        """Draw line."""
        raise NotImplementedError

    def path(self, commands: PathCommands, style: Style) -> None:
        """Draw path."""
        raise NotImplementedError

    def text(
        self, text: str, point: np.ndarray, color: Color = Color("black")
    ) -> None:
        """Draw text."""
        raise NotImplementedError

    def write(self) -> None:
        """Write image to the file."""
        raise NotImplementedError


class SVGDrawing(Drawing):
    """SVG image."""

    def __init__(self, file_path: Path, width: int, height: int) -> None:
        super().__init__(file_path, width, height)
        self.image: svgwrite.Drawing = svgwrite.Drawing(
            str(file_path), (width, height)
        )

    def rectangle(
        self, point_1: np.ndarray, point_2: np.ndarray, style: Style
    ) -> None:
        """Draw rectangle."""
        size: np.ndarray = point_2 - point_1
        rectangle: Rect = Rect(
            (float(point_1[0]), float(point_1[1])),
            (float(size[0]), float(size[1])),
        )
        style.update_svg_element(rectangle)
        self.image.add(rectangle)

    def line(self, points: List[np.ndarray], style: Style) -> None:
        """Draw line."""
        commands: PathCommands = ["M"]
        for point in points:
            commands += [point, "L"]
        self.path(commands[:-1], style)

    def path(self, commands: PathCommands, style: Style) -> None:
        """Draw path."""
        path: SVGPath = SVGPath(d=commands)
        style.update_svg_element(path)
        self.image.add(path)

    def text(
        self, text: str, point: np.ndarray, color: Color = Color("black")
    ) -> None:
        """Draw text."""
        self.image.add(
            Text(text, (float(point[0]), float(point[1])), fill=color)
        )

    def write(self) -> None:
        """Write image to the SVG file."""
        with self.file_path.open("w+", encoding="utf-8") as output_file:
            self.image.write(output_file)


def parse_path(path: str) -> PathCommands:
    """Parse path command from text representation into list."""
    parts: List[str] = path.split(" ")
    result: PathCommands = []
    command: str = "M"
    index: int = 0
    while index < len(parts):
        part: str = parts[index]
        if part in "CcLlMmZzVvHh":
            result.append(part)
            command = part
        elif command in "VvHh":
            result.append(float(part))
        else:
            if "," in part:
                elements: List[str] = part.split(",")
                result.append(np.array(list(map(float, elements))))
            else:
                result.append(np.array((float(part), float(parts[index + 1]))))
                index += 1
        index += 1

    return result


def draw_text(
    svg: svgwrite.Drawing,
    text: str,
    point: np.ndarray,
    size: float,
    fill: Color,
    anchor: str = "middle",
    stroke_linejoin: str = "round",
    stroke_width: float = 1.0,
    stroke: Optional[Color] = None,
    opacity: float = 1.0,
):
    """Add text element to the canvas."""
    text_element = svg.text(
        text,
        point,
        font_size=size,
        text_anchor=anchor,
        font_family=DEFAULT_FONT,
        fill=fill.hex,
        stroke_linejoin=stroke_linejoin,
        stroke_width=stroke_width,
        stroke=stroke.hex if stroke else "none",
        opacity=opacity,
    )
    svg.add(text_element)
