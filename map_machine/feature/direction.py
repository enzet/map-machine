"""
Direction tag support.
"""
from typing import Iterator, Optional

import numpy as np
from portolan import middle

from map_machine.drawing import PathCommands

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

SHIFT: float = -np.pi / 2
SMALLEST_ANGLE: float = np.pi / 15
DEFAULT_ANGLE: float = np.pi / 30


def parse_vector(text: str) -> Optional[np.ndarray]:
    """
    Parse vector from text representation: compass points or 360-degree
    notation.  E.g. "NW", "270".

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
            self.main_direction = (self.start + self.end) / 2
        else:
            result_angle: float
            if angle is None:
                result_angle = DEFAULT_ANGLE
            else:
                result_angle = max(SMALLEST_ANGLE, np.radians(angle) / 2)

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
            if np.allclose(self.main_direction[0], 0):
                return None
            if self.main_direction[0] > 0:
                return True
            return False

        return None

    def __str__(self) -> str:
        return f"{self.start}-{self.end}"


class DirectionSet:
    """Describes direction, set of directions."""

    def __init__(self, text: str) -> None:
        """
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
        result: list[bool] = [x.is_right() for x in self.sectors]
        if result == [True] * len(result):
            return True
        if result == [False] * len(result):
            return False
        return None
