"""Crater on the map."""

import numpy as np
from colour import Color
from svgwrite import Drawing

from map_machine.geometry.flinger import Flinger
from map_machine.osm.osm_reader import Tagged


class Crater(Tagged):
    """Volcano or impact crater on the map."""

    def __init__(
        self, tags: dict[str, str], coordinates: np.ndarray, point: np.ndarray
    ) -> None:
        super().__init__(tags)
        self.coordinates: np.ndarray = coordinates
        self.point: np.ndarray = point

    def draw(self, svg: Drawing, flinger: Flinger) -> None:
        """Draw crater ridge."""
        scale: float = flinger.get_scale(self.coordinates)
        assert "diameter" in self.tags
        radius: float = float(self.tags["diameter"]) / 2.0
        radial_gradient = svg.radialGradient(
            center=self.point + np.array((0.0, radius * scale / 7.0)),
            r=radius * scale,
            gradientUnits="userSpaceOnUse",
        )
        color: Color = Color("#000000")
        gradient = svg.defs.add(radial_gradient)
        (
            gradient
            .add_stop_color(0.0, color.hex, opacity=0.2)
            .add_stop_color(0.7, color.hex, opacity=0.2)
            .add_stop_color(1.0, color.hex, opacity=1.0)
        )  # fmt: skip
        circle = svg.circle(
            self.point,
            radius * scale,
            fill=gradient.get_funciri(),
            opacity=0.2,
        )
        svg.add(circle)
