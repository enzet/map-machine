"""Rectangle that limit space on the map."""

import logging
import re
from dataclasses import dataclass
from typing import Optional

import numpy as np

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

LATITUDE_MAX_DIFFERENCE: float = 0.5
LONGITUDE_MAX_DIFFERENCE: float = 0.5

FLOAT_PATTERN: str = r"[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?"
BOUNDING_BOX_PATTERN: re.Pattern = re.compile(
    rf"(?P<left>{FLOAT_PATTERN}),"
    rf"(?P<bottom>{FLOAT_PATTERN}),"
    rf"(?P<right>{FLOAT_PATTERN}),"
    rf"(?P<top>{FLOAT_PATTERN})"
)


@dataclass
class BoundingBox:
    """Rectangle that limit space on the map."""

    left: float  # Minimum longitude.
    bottom: float  # Minimum latitude.
    right: float  # Maximum longitude.
    top: float  # Maximum latitude.

    @classmethod
    def from_text(cls, bounding_box: str) -> Optional["BoundingBox"]:
        """Parse bounding box string representation.

        Note, that:
            left < right
            bottom < top

        :param bounding_box: bounding box string representation in the form of
            <minimum longitude>,<minimum latitude>,
            <maximum longitude>,<maximum latitude> or simply
            <left>,<bottom>,<right>,<top>.
        """
        bounding_box = bounding_box.replace(" ", "")

        matcher: Optional[re.Match] = BOUNDING_BOX_PATTERN.match(bounding_box)

        if not matcher:
            logging.fatal("Invalid bounding box.")
            return None

        try:
            left: float = float(matcher.group("left"))
            bottom: float = float(matcher.group("bottom"))
            right: float = float(matcher.group("right"))
            top: float = float(matcher.group("top"))
        except ValueError:
            logging.fatal("Invalid bounding box.")
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
            logging.error("Bounding box is too big.")
            return None

        return cls(left, bottom, right, top)

    @classmethod
    def from_coordinates(
        cls,
        coordinates: np.ndarray,
        zoom_level: float,
        width: float,
        height: float,
    ) -> "BoundingBox":
        """Compute bounding box from center coordinates, zoom level and image size.

        :param coordinates: bounding box central coordinates
        :param zoom_level: resulting image zoom level
        :param width: resulting image width
        :param height: resulting image height
        """
        lat_rad: np.ndarray = np.radians(coordinates[0])
        n: float = 2.0 ** (zoom_level + 8.0)

        x: int = int((coordinates[1] + 180.0) / 360.0 * n)
        left: float = (x - width / 2.0) / n * 360.0 - 180.0
        right: float = (x + width / 2.0) / n * 360.0 - 180.0

        y: int = (1.0 - np.arcsinh(np.tan(lat_rad)) / np.pi) / 2.0 * n
        bottom_radians = np.arctan(
            np.sinh((1.0 - (y + height / 2.0) * 2.0 / n) * np.pi)
        )
        top_radians = np.arctan(
            np.sinh((1.0 - (y - height / 2.0) * 2.0 / n) * np.pi)
        )

        return cls(
            left,
            float(np.degrees(bottom_radians)),
            right,
            float(np.degrees(top_radians)),
        )

    def min_(self) -> np.ndarray:
        """Get minimum coordinates."""
        return np.array((self.bottom, self.left))

    def max_(self) -> np.ndarray:
        """Get maximum coordinates."""
        return np.array((self.top, self.right))

    def get_left_top(self) -> np.ndarray:
        """Get left top corner of the bounding box."""
        return np.array((self.top, self.left))

    def get_right_bottom(self) -> np.ndarray:
        """Get right bottom corner of the bounding box."""
        return np.array((self.bottom, self.right))

    def round(self) -> "BoundingBox":
        """Round bounding box."""
        self.left = round(self.left * 1000.0) / 1000.0 - 0.001
        self.bottom = round(self.bottom * 1000.0) / 1000.0 - 0.001
        self.right = round(self.right * 1000.0) / 1000.0 + 0.001
        self.top = round(self.top * 1000.0) / 1000.0 + 0.001

        return self

    def center(self) -> np.ndarray:
        """Return center point of bounding box."""
        return np.array(
            ((self.top + self.bottom) / 2.0, (self.left + self.right) / 2.0)
        )

    def get_format(self) -> str:
        """Get text representation of the bounding box.

        Bounding box format is
        <longitude 1>,<latitude 1>,<longitude 2>,<latitude 2>.  Coordinates are
        rounded to three digits after comma.
        """
        left: float = np.floor(self.left * 1000.0) / 1000.0
        bottom: float = np.floor(self.bottom * 1000.0) / 1000.0
        right: float = np.ceil(self.right * 1000.0) / 1000.0
        top: float = np.ceil(self.top * 1000.0) / 1000.0

        return f"{left:.3f},{bottom:.3f},{right:.3f},{top:.3f}"

    def update(self, coordinates: np.ndarray) -> None:
        """Make the bounding box cover coordinates."""
        self.left = min(self.left, coordinates[1])
        self.bottom = min(self.bottom, coordinates[0])
        self.right = max(self.right, coordinates[1])
        self.top = max(self.top, coordinates[0])

    def combine(self, other: "BoundingBox") -> None:
        """Combine with another bounding box."""
        self.left = min(self.left, other.left)
        self.bottom = min(self.bottom, other.bottom)
        self.right = max(self.right, other.right)
        self.top = max(self.top, other.top)
