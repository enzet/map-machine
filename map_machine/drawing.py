"""Drawing utility."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import cairo
import numpy as np
import svgwrite
from cairo import Context, ImageSurface
from colour import Color
from svgwrite.base import BaseElement
from svgwrite.path import Path as SVGPath
from svgwrite.shapes import Rect
from svgwrite.text import Text

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

PathCommands = list[Union[float, str, np.ndarray]]

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

    def draw_png_fill(self, context: Context) -> None:
        """Set style for context and draw fill."""
        context.set_source_rgba(
            self.fill.get_red(), self.fill.get_green(), self.fill.get_blue()
        )
        context.fill()

    def draw_png_stroke(self, context: Context) -> None:
        """Set style for context and draw stroke."""
        context.set_source_rgba(
            self.stroke.get_red(),
            self.stroke.get_green(),
            self.stroke.get_blue(),
        )
        context.set_line_width(self.width)
        context.stroke()


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

    def line(self, points: list[np.ndarray], style: Style) -> None:
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

    def line(self, points: list[np.ndarray], style: Style) -> None:
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


class PNGDrawing(Drawing):
    """PNG image."""

    def __init__(self, file_path: Path, width: int, height: int) -> None:
        super().__init__(file_path, width, height)
        self.surface: ImageSurface = ImageSurface(
            cairo.FORMAT_ARGB32, width, height
        )
        self.context: Context = Context(self.surface)

    def rectangle(
        self, point_1: np.ndarray, point_2: np.ndarray, style: Style
    ) -> None:
        """Draw rectangle."""
        size: np.ndarray = point_2 - point_1

        if style.fill is not None:
            self.context.rectangle(point_1[0], point_1[1], size[0], size[1])
            style.draw_png_fill(self.context)
        if style.stroke is not None:
            self.context.rectangle(point_1[0], point_1[1], size[0], size[1])
            style.draw_png_stroke(self.context)

    def line(self, points: list[np.ndarray], style: Style) -> None:
        """Draw line."""
        if style.fill is not None:
            self.context.move_to(float(points[0][0]), float(points[0][1]))
            for point in points[1:]:
                self.context.line_to(float(point[0]), float(point[1]))
            style.draw_png_fill(self.context)
        if style.stroke is not None:
            self.context.move_to(float(points[0][0]), float(points[0][1]))
            for point in points[1:]:
                self.context.line_to(float(point[0]), float(point[1]))
            style.draw_png_stroke(self.context)

    def _do_path(self, commands: PathCommands) -> None:
        """Draw path."""
        current: np.ndarray = np.array((0.0, 0.0))
        start_point: Optional[np.ndarray] = None
        command: str = "M"
        is_absolute: bool = True

        index: int = 0
        while index < len(commands):
            element: Union[float, str, np.ndarray] = commands[index]

            if isinstance(element, str):
                is_absolute: bool = element.lower() != element
                command: str = element.lower()
                if command == "z":
                    self.context.line_to(start_point[0], start_point[1])
                    current = start_point
                    start_point = None

            elif command in "ml":
                point: np.ndarray
                if is_absolute:
                    point = commands[index]
                else:
                    point = current + commands[index]
                current = point
                if command == "m":
                    self.context.move_to(point[0], point[1])
                if command == "l":
                    self.context.line_to(point[0], point[1])
                if start_point is None:
                    start_point = point

            elif command == "c":
                if is_absolute:
                    point_1: np.ndarray = commands[index]
                    point_2: np.ndarray = commands[index + 1]
                    point_3: np.ndarray = commands[index + 2]
                else:
                    point_1: np.ndarray = current + commands[index]
                    point_2: np.ndarray = current + commands[index + 1]
                    point_3: np.ndarray = current + commands[index + 2]
                current = point_3
                self.context.curve_to(
                    point_1[0], point_1[1],
                    point_2[0], point_2[1],
                    point_3[0], point_3[1],
                )  # fmt: skip
                if start_point is None:
                    start_point = point_1
                index += 2

            elif command in "vh":
                assert isinstance(commands[index], float)
                point: np.ndarray
                if is_absolute:
                    if command == "v":
                        point = np.array((0.0, commands[index]))
                    else:
                        point = np.array((commands[index], 0.0))
                else:
                    if command == "v":
                        point = current + np.array((0.0, commands[index]))
                    else:
                        point = current + np.array((commands[index], 0.0))
                current = point
                self.context.line_to(point[0], point[1])
                if start_point is None:
                    start_point = point

            else:
                raise NotImplementedError

            index += 1

    def path(self, commands: PathCommands, style: Style) -> None:
        """Draw path."""
        if style.fill is not None:
            self._do_path(commands)
            style.draw_png_fill(self.context)
        if style.stroke is not None:
            self._do_path(commands)
            style.draw_png_stroke(self.context)

    def text(
        self, text: str, point: np.ndarray, color: Color = Color("black")
    ) -> None:
        """Draw text."""
        self.context.set_source_rgb(
            color.get_red(), color.get_green(), color.get_blue()
        )
        self.context.move_to(float(point[0]), float(point[1]))
        self.context.show_text(text)

    def write(self) -> None:
        """Write image to the PNG file."""
        self.surface.write_to_png(str(self.file_path))


def parse_path(path: str) -> PathCommands:
    """Parse path command from text representation into list."""
    parts: list[str] = path.split(" ")
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
                elements: list[str] = part.split(",")
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
