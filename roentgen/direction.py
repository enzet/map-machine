"""
Direction tag support.

Author: Sergey Vartanov (me@enzet.ru).
"""
import math
import numpy as np

from typing import Dict, List, Optional, Iterator


DIRECTIONS: Dict[str, np.array] = {
    "N": np.array((0, -1)),
    "E": np.array((1, 0)),
    "W": np.array((-1, 0)),
    "S": np.array((0, 1)),
}


def parse_vector(text: str) -> np.array:
    """
    Parse vector from text representation: letters N, E, W, S or 360-degree
    notation.  E.g. NW, 270.

    :param text: vector text representation
    :return: parsed normalized vector
    """
    try:
        degree: float = float(text) / 180 * math.pi - math.pi / 2
        return np.array((math.cos(degree), math.sin(degree)))
    except ValueError as e:
        vector: np.array = np.array((0, 0))
        for char in text:  # type: str
            if char not in DIRECTIONS:
                return None
            vector += DIRECTIONS[char]
        return vector / np.linalg.norm(vector)


class Sector:
    def __init__(self, text: str):
        self.start: Optional[np.array]
        self.end: Optional[np.array]

        if "-" in text:
            parts: List[str] = text.split("-")
            self.start = parse_vector(parts[0])
            self.end = parse_vector(parts[1])
        else:
            self.start = parse_vector(text)
            self.end = None

    def draw(self, center: np.array, radius: float) -> List:
        """
        Construct SVG "d" for arc element.

        :param center: arc center
        :param radius: arc radius
        """
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

    def draw(self, center: np.array, radius: float) -> Iterator[str]:
        return map(lambda x: x.draw(center, radius), self.sectors)
