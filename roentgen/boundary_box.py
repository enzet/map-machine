import logging
import re
from dataclasses import dataclass

import numpy as np

LATITUDE_MAX_DIFFERENCE: float = 0.5
LONGITUDE_MAX_DIFFERENCE: float = 0.5


@dataclass
class BoundaryBox:
    """
    Rectangle that limit space on the map.
    """

    left: float  # Minimum longitude.
    bottom: float  # Minimum latitude.
    right: float  # Maximum longitude.
    top: float  # Maximum latitude.

    @classmethod
    def from_text(cls, boundary_box: str):
        """
        Parse boundary box string representation.

        Note, that:
            left < right
            bottom < top

        :param boundary_box: boundary box string representation in the form of
            <minimum longitude>,<minimum latitude>,
            <maximum longitude>,<maximum latitude> or simply
            <left>,<bottom>,<right>,<top>.
        """
        boundary_box = boundary_box.replace(" ", "")

        matcher = re.match(
            "(?P<left>[0-9.-]*),(?P<bottom>[0-9.-]*),"
            + "(?P<right>[0-9.-]*),(?P<top>[0-9.-]*)",
            boundary_box,
        )

        if not matcher:
            logging.fatal("Invalid boundary box.")
            return None

        try:
            left: float = float(matcher.group("left"))
            bottom: float = float(matcher.group("bottom"))
            right: float = float(matcher.group("right"))
            top: float = float(matcher.group("top"))
        except ValueError:
            logging.fatal("Invalid boundary box.")
            return None

        if left >= right:
            logging.fatal("Negative horizontal boundary.")
            return None
        if bottom >= top:
            logging.error("Negative vertical boundary.")
            return None
        if (
            right - left > LONGITUDE_MAX_DIFFERENCE
            or top - bottom > LATITUDE_MAX_DIFFERENCE
        ):
            logging.error("Boundary box is too big.")
            return None

        return cls(left, bottom, right, top)

    def min_(self) -> np.ndarray:
        """Get minimum coordinates."""
        return np.array((self.bottom, self.left))

    def max_(self) -> np.ndarray:
        """Get maximum coordinates."""
        return np.array((self.top, self.right))

    def get_left_top(self) -> (np.ndarray, np.ndarray):
        """Get left top corner of the boundary box."""
        return self.top, self.left

    def get_right_bottom(self) -> (np.ndarray, np.ndarray):
        """Get right bottom corner of the boundary box."""
        return self.bottom, self.right

    def round(self) -> "BoundaryBox":
        """Round boundary box."""
        self.left = round(self.left * 1000) / 1000 - 0.001
        self.bottom = round(self.bottom * 1000) / 1000 - 0.001
        self.right = round(self.right * 1000) / 1000 + 0.001
        self.top = round(self.top * 1000) / 1000 + 0.001

        return self

    def center(self) -> np.ndarray:
        """Return center point of boundary box."""
        return np.array(
            ((self.left + self.right) / 2, (self.top + self.bottom) / 2)
        )

    def get_format(self) -> str:
        """
        Get text representation of the boundary box:
        <longitude 1>,<latitude 1>,<longitude 2>,<latitude 2>.  Coordinates are
        rounded to three digits after comma.
        """
        return (
            f"{self.left:.3f},{self.bottom:.3f},{self.right:.3f},{self.top:.3f}"
        )
