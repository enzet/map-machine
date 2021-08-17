"""
Drawing utility.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

import cairo
import numpy as np
import svgwrite
from colour import Color
from svgwrite.shapes import Rect
from svgwrite.path import Path as SVGPath
from svgwrite.text import Text


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

    def __init__(self, file_path: Path, width: int, height: int):
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

    def __init__(self, file_path: Path, width: int, height: int):
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
        commands: str = "M "
        for point in points:
            commands += f"{point[0]},{point[1]} L "
        path = SVGPath(d=commands[:-3])
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

    def __init__(self, file_path: Path, width: int, height: int):
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
