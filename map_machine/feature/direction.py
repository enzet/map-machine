"""Direction tag support."""

from typing import Iterator, Optional

import numpy as np
from colour import Color
from portolan import middle
from svgwrite import Drawing
from svgwrite.gradients import RadialGradient
from svgwrite.path import Path

from map_machine.drawing import PathCommands
from map_machine.osm.osm_reader import Tagged

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

SHIFT: float = -np.pi / 2.0
SMALLEST_ANGLE: float = np.pi / 15.0
DEFAULT_ANGLE: float = np.pi / 30.0


def parse_vector(text: str) -> Optional[np.ndarray]:
    """
    Parse vector from text representation.

    Compass points or 360-degree notation.  E.g. "NW", "270".

    :param text: vector text representation
    :return: parsed normalized vector
    """
    try:
        radians: float = np.radians(float(text)) + SHIFT
        return np.array((np.cos(radians), np.sin(radians)))
    except ValueError:
        pass

    try:
        radians: float = np.radians(middle(text)) + SHIFT
        return np.array((np.cos(radians), np.sin(radians)))
    except KeyError:
        pass

    return None


def rotation_matrix(angle: float) -> np.ndarray:
    """
    Get a matrix to rotate 2D vector by the angle.

    :param angle: angle in radians
    """
    return np.array(
        [[np.cos(angle), np.sin(angle)], [-np.sin(angle), np.cos(angle)]]
    )


class Sector:
    """Sector described by two vectors."""

    def __init__(self, text: str, angle: Optional[float] = None) -> None:
        """
        Construct sector from text representation.

        :param text: sector text representation (e.g. "70-210", "N-NW")
        :param angle: angle in degrees
        """
        self.start: Optional[np.ndarray] = None
        self.end: Optional[np.ndarray] = None
        self.main_direction: Optional[np.ndarray] = None

        if "-" in text and not text.startswith("-"):
            parts: list[str] = text.split("-")
            self.start = parse_vector(parts[0])
            self.end = parse_vector(parts[1])
            self.main_direction = (self.start + self.end) / 2.0
        else:
            result_angle: float
            if angle is None:
                result_angle = DEFAULT_ANGLE
            else:
                result_angle = max(SMALLEST_ANGLE, np.radians(angle) / 2.0)

            vector: Optional[np.ndarray] = parse_vector(text)
            self.main_direction = vector

            if vector is not None:
                self.start = np.dot(rotation_matrix(result_angle), vector)
                self.end = np.dot(rotation_matrix(-result_angle), vector)

    def draw(self, center: np.ndarray, radius: float) -> Optional[PathCommands]:
        """
        Construct SVG path commands for arc element.

        :param center: arc center point
        :param radius: arc radius
        :return: SVG path commands
        """
        if self.start is None or self.end is None:
            return None

        start: np.ndarray = center + radius * self.end
        end: np.ndarray = center + radius * self.start

        return ["L", start, "A", radius, radius, 0, "0", 0, end]

    def is_right(self) -> Optional[bool]:
        """
        Check if main direction of the sector is right.

        :return: true if direction is right, false if direction is left, and
            None otherwise.
        """
        if self.main_direction is not None:
            if np.allclose(self.main_direction[0], 0.0):
                return None
            if self.main_direction[0] > 0.0:
                return True
            return False

        return None

    def __str__(self) -> str:
        return f"{self.start}-{self.end}"


class DirectionSet:
    """Describes direction, set of directions."""

    def __init__(self, text: str) -> None:
        """
        Construct direction set from text representation.

        :param text: direction tag value
        """
        self.sectors: Iterator[Optional[Sector]] = map(Sector, text.split(";"))

    def __str__(self) -> str:
        return ", ".join(map(str, self.sectors))

    def draw(self, center: np.ndarray, radius: float) -> Iterator[PathCommands]:
        """
        Construct SVG "d" for arc elements.

        :param center: center point of all arcs
        :param radius: radius of all arcs
        :return: list of "d" values
        """
        return filter(
            lambda x: x is not None,
            map(lambda x: x.draw(center, radius), self.sectors),
        )

    def is_right(self) -> Optional[bool]:
        """
        Check if main direction of the sector is right.

        :return: true if direction is right, false if direction is left, and
            None otherwise.
        """
        result: list[bool] = [sector.is_right() for sector in self.sectors]
        if result == [True] * len(result):
            return True
        if result == [False] * len(result):
            return False
        return None


class DirectionSector(Tagged):
    """Sector that represents direction."""

    def __init__(self, tags: dict[str, str], point: np.ndarray) -> None:
        super().__init__(tags)
        self.point: np.ndarray = point

    def draw(self, svg: Drawing, scheme) -> None:
        """Draw gradient sector."""
        angle: Optional[float] = None
        is_revert_gradient: bool = False
        direction: str
        direction_radius: float
        direction_color: Color

        if self.get_tag("man_made") == "surveillance":
            direction = self.get_tag("camera:direction")
            if "camera:angle" in self.tags:
                angle = float(self.get_tag("camera:angle"))
            if "angle" in self.tags:
                angle = float(self.get_tag("angle"))
            direction_radius = 50.0
            direction_color = scheme.get_color("direction_camera_color")
        elif self.get_tag("traffic_sign") == "stop":
            direction = self.get_tag("direction")
            direction_radius = 25.0
            direction_color = Color("red")
        else:
            direction = self.get_tag("direction")
            direction_radius = 50.0
            direction_color = scheme.get_color("direction_view_color")
            is_revert_gradient = True

        if not direction:
            return

        point: np.ndarray = (self.point.astype(int)).astype(float)

        paths: Iterator[PathCommands]
        if angle is not None:
            paths = [Sector(direction, angle).draw(point, direction_radius)]
        else:
            paths = DirectionSet(direction).draw(point, direction_radius)

        for path in paths:
            radial_gradient: RadialGradient = svg.radialGradient(
                center=point,
                r=direction_radius,
                gradientUnits="userSpaceOnUse",
            )
            gradient: RadialGradient = svg.defs.add(radial_gradient)

            if is_revert_gradient:
                (
                    gradient
                    .add_stop_color(0.0, direction_color.hex, opacity=0.0)
                    .add_stop_color(1.0, direction_color.hex, opacity=0.7)
                )  # fmt: skip
            else:
                (
                    gradient
                    .add_stop_color(0.0, direction_color.hex, opacity=0.4)
                    .add_stop_color(1.0, direction_color.hex, opacity=0.0)
                )  # fmt: skip

            path_element: Path = svg.path(
                d=["M", point] + path + ["L", point, "Z"],
                fill=gradient.get_funciri(),
            )
            svg.add(path_element)
