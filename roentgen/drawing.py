"""
Drawing utility.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Union

import cairo
import numpy as np
import svgwrite
from colour import Color
from svgwrite.path import Path as SVGPath
from svgwrite.shapes import Rect
from svgwrite.text import Text

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

PathCommands = list[Union[float, str, np.array]]


@dataclass
class Style:
    """
    Drawing element style.
    """

    fill: Optional[Color] = None
    stroke: Optional[Color] = None
    width: float = 1

    def update_svg_element(self, element) -> None:
        """Set style for SVG element."""
        if self.fill is not None:
            element.update({"fill": self.fill})
        else:
            element.update({"fill": "none"})
        if self.stroke is not None:
            element.update({"stroke": self.stroke, "stroke-width": self.width})

    def draw_png_fill(self, context) -> None:
        """Set style for context and draw fill."""
        context.set_source_rgba(
            self.fill.get_red(), self.fill.get_green(), self.fill.get_blue(), 1
        )
        context.fill()

    def draw_png_stroke(self, context) -> None:
        """Set style for context and draw stroke."""
        context.set_source_rgba(
            self.stroke.get_red(),
            self.stroke.get_green(),
            self.stroke.get_blue(),
            1,
        )
        context.set_line_width(self.width)
        context.stroke()


class Drawing:
    """
    Image.
    """

    def __init__(self, file_path: Path, width: int, height: int) -> None:
        self.file_path: Path = file_path
        self.width: int = width
        self.height: int = height

    def rectangle(
        self, point_1: np.array, point_2: np.array, style: Style
    ) -> None:
        """Draw rectangle."""
        raise NotImplementedError

    def line(self, points: List[np.array], style: Style) -> None:
        """Draw line."""
        raise NotImplementedError

    def path(self, commands: PathCommands, style: Style) -> None:
        """Draw path."""
        raise NotImplementedError

    def text(self, text: str, point: np.array, color: Color = Color("black")):
        """Draw text."""
        raise NotImplementedError

    def write(self) -> None:
        """Write image to the file."""
        raise NotImplementedError


class SVGDrawing(Drawing):
    """
    SVG image.
    """

    def __init__(self, file_path: Path, width: int, height: int) -> None:
        super().__init__(file_path, width, height)
        self.image = svgwrite.Drawing(str(file_path), (width, height))

    def rectangle(
        self, point_1: np.array, point_2: np.array, style: Style
    ) -> None:
        """Draw rectangle."""
        size: np.array = point_2 - point_1
        rectangle: Rect = Rect(
            (float(point_1[0]), float(point_1[1])),
            (float(size[0]), float(size[1])),
        )
        style.update_svg_element(rectangle)
        self.image.add(rectangle)

    def line(self, points: List[np.array], style: Style) -> None:
        """Draw line."""
        commands: PathCommands = ["M"]
        for point in points:
            commands += [point, "L"]
        self.path(commands[:-1], style)

    def path(self, commands: PathCommands, style: Style) -> None:
        """Draw path."""
        path = SVGPath(d=commands)
        style.update_svg_element(path)
        self.image.add(path)

    def text(self, text: str, point: np.array, color: Color = Color("black")):
        """Draw text."""
        self.image.add(
            Text(text, (float(point[0]), float(point[1])), fill=color)
        )

    def write(self) -> None:
        """Write image to the SVG file."""
        with self.file_path.open("w+") as output_file:
            self.image.write(output_file)


class PNGDrawing(Drawing):
    """
    PNG image.
    """

    def __init__(self, file_path: Path, width: int, height: int) -> None:
        super().__init__(file_path, width, height)
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        self.context = cairo.Context(self.surface)

    def rectangle(
        self, point_1: np.array, point_2: np.array, style: Style
    ) -> None:
        """Draw rectangle."""
        size: np.array = point_2 - point_1

        if style.fill is not None:
            self.context.rectangle(point_1[0], point_1[1], size[0], size[1])
            style.draw_png_fill(self.context)
        if style.stroke is not None:
            self.context.rectangle(point_1[0], point_1[1], size[0], size[1])
            style.draw_png_stroke(self.context)

    def line(self, points: List[np.array], style: Style) -> None:
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

    def _do_path(self, commands) -> None:
        """Draw path."""
        current = np.array((0, 0))
        command: str = "M"
        is_absolute: bool = True

        index: int = 0
        while index < len(commands):
            element = commands[index]

            if isinstance(element, str):
                is_absolute: bool = element.lower() != element
                command: str = element.lower()

            elif command in "ml":
                if is_absolute:
                    point: np.array = commands[index]
                else:
                    point: np.array = current + commands[index]
                    current = point
                if command == "m":
                    self.context.move_to(point[0], point[1])
                if command == "l":
                    self.context.line_to(point[0], point[1])

            elif command == "c":
                if is_absolute:
                    point_1: np.array = commands[index]
                    point_2: np.array = commands[index + 1]
                    point_3: np.array = commands[index + 2]
                else:
                    point_1: np.array = current + commands[index]
                    point_2: np.array = current + commands[index + 1]
                    point_3: np.array = current + commands[index + 2]
                    current = point_3
                self.context.curve_to(
                    point_1[0], point_1[1],
                    point_2[0], point_2[1],
                    point_3[0], point_3[1],
                )  # fmt: skip
                index += 2

            index += 1

    def path(self, commands: PathCommands, style: Style) -> None:
        """Draw path."""
        if style.fill is not None:
            self._do_path(commands)
            style.draw_png_fill(self.context)
        if style.stroke is not None:
            self._do_path(commands)
            style.draw_png_stroke(self.context)

    def text(self, text: str, point: np.array, color: Color = Color("black")):
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
    for part in parts:
        if part in "CcLlMmZz":
            result.append(part)
        else:
            elements = part.split(",")
            assert len(elements) == 2
            result.append(np.array((float(elements[0]), float(elements[1]))))
    return result
