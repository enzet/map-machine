"""
Vector utility.
"""
import numpy as np

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

from shapely.geometry import LineString


def compute_angle(vector: np.ndarray) -> float:
    """
    For the given vector compute an angle between it and (1, 0) vector.  The
    result is in [0, 2π].
    """
    if vector[0] == 0:
        if vector[1] > 0:
            return np.pi / 2
        return np.pi + np.pi / 2
    if vector[0] < 0:
        return np.arctan(vector[1] / vector[0]) + np.pi
    if vector[1] < 0:
        return np.arctan(vector[1] / vector[0]) + 2 * np.pi
    return np.arctan(vector[1] / vector[0])


def turn_by_angle(vector: np.ndarray, angle: float) -> np.ndarray:
    """Turn vector by an angle."""
    return np.array(
        (
            vector[0] * np.cos(angle) - vector[1] * np.sin(angle),
            vector[0] * np.sin(angle) + vector[1] * np.cos(angle),
        )
    )


def norm(vector: np.ndarray) -> np.ndarray:
    """Compute vector with the same direction and length 1."""
    return vector / np.linalg.norm(vector)


class Polyline:
    """
    List of connected points.
    """

    def __init__(self, points: list[np.ndarray]) -> None:
        self.points: list[np.ndarray] = points

    def get_path(self, parallel_offset: float = 0) -> str:
        """Construct SVG path commands."""
        points: list[np.ndarray]
        if np.allclose(parallel_offset, 0):
            points = self.points
        else:
            try:
                points = (
                    LineString(self.points)
                    .parallel_offset(parallel_offset)
                    .coords
                    if parallel_offset
                    else self.points
                )
            except ValueError:
                points = self.points
        path: str = "M " + " L ".join(f"{x[0]},{x[1]}" for x in points)
        return path + (" Z" if np.allclose(points[0], points[-1]) else "")

    def shorten(self, index: int, length: float) -> None:
        """Make shorten part specified with index."""
        index_2: int = 1 if index == 0 else -2
        diff: np.ndarray = self.points[index_2] - self.points[index]
        self.points[index] = (
            self.points[index] + diff / np.linalg.norm(diff) * length
        )


class Line:
    """Infinity line: Ax + By + C = 0."""

    def __init__(self, start: np.ndarray, end: np.ndarray) -> None:
        # if start.near(end):
        #     util.error("cannot create line by one point")
        self.a: float = start[1] - end[1]
        self.b: float = end[0] - start[0]
        self.c: float = start[0] * end[1] - end[0] * start[1]

    def parallel_shift(self, shift: np.ndarray) -> None:
        """
        Shift current vector according with shift.

        :param shift: shift vector
        """
        self.c -= self.a * shift[0] + self.b * shift[1]

    def is_parallel(self, other: "Line") -> bool:
        """If lines are parallel or equal."""
        return np.allclose(other.a * self.b - self.a * other.b, 0)

    def get_intersection_point(self, other: "Line") -> np.ndarray:
        """Get point of intersection current line with other."""
        if other.a * self.b - self.a * other.b == 0:
            return np.array((0, 0))

        x: float = -(self.b * other.c - other.b * self.c) / (
            other.a * self.b - self.a * other.b
        )
        y: float = -(self.a * other.c - other.a * self.c) / (
            other.b * self.a - self.b * other.a
        )
        return np.array((x, y))

    def __repr__(self) -> str:
        return f"{self.a} * x + {self.b} * y + {self.c} == 0"
