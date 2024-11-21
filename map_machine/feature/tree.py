"""
Drawing tree features on the map.

If radius of trunk or crown are specified they are displayed with simple
circles.
"""

import numpy as np
from colour import Color
from svgwrite import Drawing

from map_machine.geometry.flinger import Flinger
from map_machine.osm.osm_reader import Tagged
from map_machine.scheme import Scheme


class Tree(Tagged):
    """Tree on the map."""

    def __init__(
        self, tags: dict[str, str], coordinates: np.ndarray, point: np.ndarray
    ) -> None:
        super().__init__(tags)
        self.coordinates: np.ndarray = coordinates
        self.point: np.ndarray = point

    def draw(self, svg: Drawing, flinger: Flinger, scheme: Scheme) -> None:
        """Draw crown and trunk."""
        scale: float = flinger.get_scale(self.coordinates)

        radius: float
        if diameter_crown := self.get_float("diameter_crown") is not None:
            radius = diameter_crown / 2.0
        else:
            radius = 2.0

        color: Color = scheme.get_color("evergreen_color")
        svg.add(svg.circle(self.point, radius * scale, fill=color, opacity=0.3))

        if (circumference := self.get_float("circumference")) is not None:
            radius: float = circumference / 2.0 / np.pi
            circle = svg.circle(
                self.point, radius * scale, fill=scheme.get_color("trunk_color")
            )
            svg.add(circle)
