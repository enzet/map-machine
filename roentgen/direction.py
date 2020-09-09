"""
Direction tag support.

Author: Sergey Vartanov (me@enzet.ru).
"""
from typing import Iterator, List, Optional, Union

import numpy as np
from portolan import middle


def parse_vector(text: str) -> np.array:
    """
    Parse vector from text representation: compass points or 360-degree
    notation.  E.g. "NW", "270".

    :param text: vector text representation
    :return: parsed normalized vector
    """
    def degree_to_radian(degree: float):
        """ Convert value in degrees to radians. """
        return degree / 180 * np.pi - np.pi / 2

    try:
        radians: float = degree_to_radian(float(text))
        return np.array((np.cos(radians), np.sin(radians)))
    except ValueError:
        radians: float = degree_to_radian(middle(text))
        return np.array((np.cos(radians), np.sin(radians)))


def rotation_matrix(angle):
    """
    Get a matrix to rotate 2D vector by the angle.

    :param angle: angle in radians
    """
    return np.array([
        [np.cos(angle), np.sin(angle)],
        [-np.sin(angle), np.cos(angle)]])


class Sector:
    """
    Sector described by two vectors.
    """
    def __init__(self, text: str):
        """
        :param text: sector text representation.  E.g. "70-210", "N-NW"
        """
        self.start: Optional[np.array]
        self.end: Optional[np.array]

        if "-" in text:
            parts: List[str] = text.split("-")
            self.start = parse_vector(parts[0])
            self.end = parse_vector(parts[1])
        else:
            vector = parse_vector(text)
            angle = np.pi / 12
            self.start = np.dot(rotation_matrix(angle), vector)
            self.end = np.dot(rotation_matrix(-angle), vector)

    def draw(self, center: np.array, radius: float) \
            -> Optional[List[Union[float, str, np.array]]]:
        """
        Construct SVG path commands for arc element.

        :param center: arc center point
        :param radius: arc radius
        :return: SVG path commands
        """
        if self.start is None or self.end is None:
            return None

        start: np.array = center + radius * self.end
        end: np.array = center + radius * self.start

        return ["L", start, "A", radius, radius, 0, "0", 0, end]

    def __str__(self):
        return f"{self.start}-{self.end}"


class DirectionSet:
    """
    Describes direction, set of directions.
    """
    def __init__(self, text: str):
        """
        :param text: direction tag value
        """
        self.sectors = list(map(Sector, text.split(";")))

    def __str__(self):
        return ", ".join(map(str, self.sectors))

    def draw(self, center: np.array, radius: float) -> Iterator[List]:
        """
        Construct SVG "d" for arc elements.

        :param center: center point of all arcs
        :param radius: radius of all arcs
        :return: list of "d" values
        """
        return filter(
            lambda x: x is not None,
            map(lambda x: x.draw(center, radius), self.sectors))
