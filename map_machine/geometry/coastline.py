"""Coastline water polygon construction for partial map data.

OSM coastlines are ways where land is on the left and water is on the right.
When downloading partial map data, coastlines appear as incomplete segments.
This module constructs closed water polygons by connecting coastline segments
along bounding box edges.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from map_machine.geometry.bounding_box import BoundingBox
    from map_machine.osm.osm_reader import OSMData, OSMNode

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

logger: logging.Logger = logging.getLogger(__name__)


class BoundingBoxEdge(IntEnum):
    """Bounding box edge identifiers in clockwise order."""

    TOP = 0
    RIGHT = 1
    BOTTOM = 2
    LEFT = 3


class IntersectionType(IntEnum):
    """Whether coastline enters or exits the bounding box."""

    ENTRY = 0
    """Coastline entering bounding box (coming from outside)."""

    EXIT = 1
    """Coastline exiting bounding box (going outside)."""


@dataclass
class BoundingBoxIntersection:
    """Point where a coastline crosses the bounding box boundary."""

    coordinates: np.ndarray
    """(latitude, longitude)"""

    edge: BoundingBoxEdge
    type_: IntersectionType

    coastline_index: int
    """Index of the coastline this belongs to."""

    segment_index: int
    """Index of segment within coastline (before this point)."""

    perimeter_position: float = 0.0
    """Position along bounding box perimeter for sorting."""


@dataclass
class WaterPolygon:
    """A closed polygon constructed from coastlines and bounding box edges."""

    points: list[np.ndarray] = field(default_factory=list)
    """(latitude, longitude) coordinates."""

    is_hole: bool = False
    """True if this is an island (land inside water)."""


def _glue_coastlines(coastlines: list[list[OSMNode]]) -> list[list[OSMNode]]:
    """Join coastline segments that share endpoints.

    This is similar to the `glue()` function in `constructor.py` but works
    specifically with coastline segments.
    """
    if not coastlines:
        return []

    result: list[list[OSMNode]] = []
    to_process: list[list[OSMNode]] = []

    for coastline in coastlines:
        if len(coastline) < 2:  # noqa: PLR2004
            continue
        if coastline[0] == coastline[-1]:
            result.append(coastline)
        else:
            to_process.append(coastline)

    while to_process:
        current: list[OSMNode] = to_process.pop(0)
        glued: bool = False

        for i, other in enumerate(to_process):
            merged = _try_merge(current, other)
            if merged is not None:
                to_process.pop(i)
                if merged[0] == merged[-1]:
                    result.append(merged)
                else:
                    to_process.append(merged)
                glued = True
                break

        if not glued:
            result.append(current)

    return result


def _try_merge(a: list[OSMNode], b: list[OSMNode]) -> list[OSMNode] | None:
    """Try to merge two coastline segments if they share an endpoint."""
    if a[-1] == b[0]:
        return a + b[1:]
    if a[-1] == b[-1]:
        return a + list(reversed(b[:-1]))
    if a[0] == b[-1]:
        return b + a[1:]
    if a[0] == b[0]:
        return list(reversed(b[1:])) + a
    return None


class CoastlineProcessor:
    """Processes coastline ways to create water polygons."""

    def __init__(self, bounding_box: BoundingBox) -> None:
        self.bounding_box: BoundingBox = bounding_box
        self._coastlines: list[list[OSMNode]] = []
        self._intersections: list[BoundingBoxIntersection] = []

    def process(self, osm_data: OSMData) -> list[WaterPolygon]:
        """Extract coastlines and construct water polygons.

        :param osm_data: OSM data containing ways
        :return: list of water polygons to render
        """
        self._coastlines = self._extract_coastlines(osm_data)

        if not self._coastlines:
            return []

        logger.info("Processing %d coastline segments.", len(self._coastlines))

        # Find all intersections with bounding box.
        self._intersections = []
        for coast_index, coastline in enumerate(self._coastlines):
            intersections = self._find_intersections(coastline, coast_index)
            self._intersections.extend(intersections)

        # Sort intersections by position along bounding box perimeter.
        self._sort_intersections_clockwise()

        # Construct water polygons.
        return self._construct_water_polygons()

    def _extract_coastlines(self, osm_data: OSMData) -> list[list[OSMNode]]:
        """Get all coastline ways and glue contiguous segments."""
        coastlines: list[list[OSMNode]] = [
            way.nodes
            for way in osm_data.ways.values()
            if (
                len(way.nodes) >= 2  # noqa: PLR2004
                and way.tags.get("natural") == "coastline"
            )
        ]

        return _glue_coastlines(coastlines)

    def _find_intersections(
        self, coastline: list[OSMNode], coastline_index: int
    ) -> list[BoundingBoxIntersection]:
        """Find all points where coastline crosses bounding box edges."""
        intersections: list[BoundingBoxIntersection] = []

        for index in range(len(coastline) - 1):
            point_1: np.ndarray = coastline[index].coordinates
            point_2: np.ndarray = coastline[index + 1].coordinates

            # Check intersection with each bounding box edge.
            for edge in BoundingBoxEdge:
                intersection = self._segment_edge_intersection(
                    point_1, point_2, edge
                )
                if intersection is not None:
                    # Determine if entering or exiting.
                    inside_point_1: bool = self.bounding_box.contains_point(
                        point_1
                    )
                    inside_point_2: bool = self.bounding_box.contains_point(
                        point_2
                    )

                    if inside_point_1 and not inside_point_2:
                        int_type = IntersectionType.EXIT
                    elif not inside_point_1 and inside_point_2:
                        int_type = IntersectionType.ENTRY
                    else:
                        # Both inside or both outside. This can happen when
                        # segment touches edge exactly.
                        continue

                    intersections.append(
                        BoundingBoxIntersection(
                            coordinates=intersection,
                            edge=edge,
                            type_=int_type,
                            coastline_index=coastline_index,
                            segment_index=index,
                        )
                    )

        return intersections

    def _segment_edge_intersection(
        self, point_1: np.ndarray, point_2: np.ndarray, edge: BoundingBoxEdge
    ) -> np.ndarray | None:
        """Check if segment intersects bounding box edge.

        Uses parametric line intersection.

        :return: intersection point
        """
        # Get edge endpoints (latitude, longitude).
        corners: list[np.ndarray] = self.bounding_box.get_corners()
        if edge == BoundingBoxEdge.TOP:
            # Top-left to top-right.
            corner_1, corner_2 = (corners[0], corners[1])
        elif edge == BoundingBoxEdge.RIGHT:
            # Top-right to bottom-right.
            corner_1, corner_2 = (corners[1], corners[2])
        elif edge == BoundingBoxEdge.BOTTOM:
            # Bottom-right to bottom-left.
            corner_1, corner_2 = (corners[2], corners[3])
        else:  # LEFT
            # Bottom-left to top-left.
            corner_1, corner_2 = (corners[3], corners[0])

        # Parametric intersection:
        #     point_1 + t * (point_2 - point_1) =
        #     corner_1 + u * (corner_2 - corner_1).
        d1 = point_2 - point_1
        d2 = corner_2 - corner_1

        cross = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(cross) < 1e-10:  # noqa: PLR2004
            return None  # Parallel.

        difference = corner_1 - point_1
        t = (difference[0] * d2[1] - difference[1] * d2[0]) / cross
        u = (difference[0] * d1[1] - difference[1] * d1[0]) / cross

        # Check if intersection is within both segments. Use small epsilon for
        # numerical stability.
        eps = 1e-9
        if -eps <= t <= 1 + eps and -eps <= u <= 1 + eps:
            return point_1 + t * d1

        return None

    def _sort_intersections_clockwise(self) -> None:
        """Sort intersection points by position along bounding box perimeter."""

        # Calculate perimeter position for each intersection. Clockwise from
        # top-left.
        for intersection in self._intersections:
            intersection.perimeter_position = self._get_perimeter_position(
                intersection.coordinates, intersection.edge
            )

        self._intersections.sort(key=lambda x: x.perimeter_position)

    def _get_perimeter_position(
        self, point: np.ndarray, edge: BoundingBoxEdge
    ) -> float:
        """Get position along bounding box perimeter.

        0 to 4, clockwise from top-left.
        """
        lat, lon = point[0], point[1]

        if edge == BoundingBoxEdge.TOP:
            # Position along top edge (left to right).
            t = (lon - self.bounding_box.left) / (
                self.bounding_box.right - self.bounding_box.left
            )
            return 0.0 + t
        if edge == BoundingBoxEdge.RIGHT:
            # Position along right edge (top to bottom).
            t = (self.bounding_box.top - lat) / (
                self.bounding_box.top - self.bounding_box.bottom
            )
            return 1.0 + t
        if edge == BoundingBoxEdge.BOTTOM:
            # Position along bottom edge (right to left).
            t = (self.bounding_box.right - lon) / (
                self.bounding_box.right - self.bounding_box.left
            )
            return 2.0 + t
        # Position along left edge (bottom to top).
        t = (lat - self.bounding_box.bottom) / (
            self.bounding_box.top - self.bounding_box.bottom
        )
        return 3.0 + t

    def _construct_water_polygons(self) -> list[WaterPolygon]:
        """Connect coastlines along bounding box edges to form polygons."""
        if not self._intersections:
            # No intersections: check if bounding box is entirely water or land.
            return self._handle_no_intersections()

        water_polygons: list[WaterPolygon] = []
        used_exits: set[int] = set()

        # Process each exit point to construct a water polygon.
        for start_index, start_int in enumerate(self._intersections):
            if start_int.type_ != IntersectionType.EXIT:
                continue
            if start_index in used_exits:
                continue

            polygon = self._trace_water_polygon(start_index, used_exits)
            if polygon and len(polygon.points) >= 3:  # noqa: PLR2004
                water_polygons.append(polygon)

        # Handle closed coastlines entirely inside bounding box (islands).
        for coast_index, coastline in enumerate(self._coastlines):
            if coastline[0] == coastline[-1]:
                # Closed coastline.
                has_intersections = any(
                    i.coastline_index == coast_index
                    for i in self._intersections
                )
                if not has_intersections:
                    # Entirely inside bounding box, it's an island.
                    polygon = WaterPolygon(is_hole=True)
                    for node in coastline:
                        polygon.points.append(node.coordinates.copy())
                    water_polygons.append(polygon)

        return water_polygons

    def _trace_water_polygon(
        self, start_index: int, used_exits: set[int]
    ) -> WaterPolygon | None:
        """Trace a water polygon starting from an exit intersection."""
        polygon = WaterPolygon()
        current_index = start_index
        used_exits.add(start_index)

        max_iterations = len(self._intersections) * 2 + 10
        iterations = 0

        while iterations < max_iterations:
            iterations += 1
            current_int = self._intersections[current_index]

            # Add the exit point.
            polygon.points.append(current_int.coordinates.copy())

            # Find next entry point by following bounding box edge clockwise.
            next_entry_index = self._find_next_entry(current_index)
            if next_entry_index is None:
                logger.warning("Could not find next entry point.")
                return None

            # Add bounding box corners between exit and entry if needed.
            bounding_box_points = self._get_bounding_box_path_points(
                current_int.perimeter_position,
                self._intersections[next_entry_index].perimeter_position,
            )
            polygon.points.extend(bounding_box_points)

            # Add the entry point.
            next_entry = self._intersections[next_entry_index]
            polygon.points.append(next_entry.coordinates.copy())

            # Follow coastline to next exit point.
            next_exit_index = self._find_coastline_exit(next_entry)
            if next_exit_index is None:
                logger.warning("Could not find exit point on coastline.")
                return None

            # Add coastline points between entry and exit.
            coastline_points = self._get_coastline_points(
                next_entry, self._intersections[next_exit_index]
            )
            polygon.points.extend(coastline_points)

            # Check if we've completed the loop.
            if next_exit_index == start_index:
                break

            if next_exit_index in used_exits:
                logger.warning("Encountered already used exit point.")
                break

            used_exits.add(next_exit_index)
            current_index = next_exit_index

        # Close the polygon.
        if polygon.points and not np.allclose(
            polygon.points[0], polygon.points[-1]
        ):
            polygon.points.append(polygon.points[0].copy())

        return polygon

    def _find_next_entry(self, from_index: int) -> int | None:
        """Find the next entry intersection clockwise from given index."""
        length = len(self._intersections)
        for offset in range(1, length + 1):
            index = (from_index + offset) % length
            if self._intersections[index].type_ == IntersectionType.ENTRY:
                return index
        return None

    def _find_coastline_exit(
        self, entry: BoundingBoxIntersection
    ) -> int | None:
        """Find the exit intersection on the same coastline after entry."""
        coast_index = entry.coastline_index

        # Find all intersections on this coastline.
        coastline_intersections: list[tuple[int, BoundingBoxIntersection]] = [
            (index, inter)
            for index, inter in enumerate(self._intersections)
            if inter.coastline_index == coast_index
        ]

        # Sort by segment index.
        coastline_intersections.sort(key=lambda x: x[1].segment_index)

        # Find the entry in sorted list and get next exit.
        entry_position = None
        for position, (_, intersection) in enumerate(coastline_intersections):
            if (
                intersection.segment_index == entry.segment_index
                and intersection.type_ == IntersectionType.ENTRY
            ):
                entry_position = position
                break

        if entry_position is None:
            return None

        # Look for next exit after this entry.
        for position in range(entry_position + 1, len(coastline_intersections)):
            index, inter = coastline_intersections[position]
            if inter.type_ == IntersectionType.EXIT:
                return index

        # Wrap around if coastline is cyclic.
        for position in range(entry_position):
            index, inter = coastline_intersections[position]
            if inter.type_ == IntersectionType.EXIT:
                return index

        return None

    def _get_bounding_box_path_points(
        self, from_position: float, to_position: float
    ) -> list[np.ndarray]:
        """Get corner points when traversing bounding box clockwise."""
        points: list[np.ndarray] = []
        corners = self.bounding_box.get_corners()

        # Handle wrap-around.
        if to_position < from_position:
            to_position += 4.0

        # Add corners between from_pos and to_pos.
        for corner_index in range(4):
            corner_position = float(corner_index + 1)  # 1, 2, 3, 4.
            if corner_position <= from_position:
                corner_position += 4.0
            if from_position < corner_position < to_position:
                actual_index = corner_index % 4
                # Corner index 0 is at position 1 (end of top edge). So corner
                # at position 1 is corners[1] (top-right).
                points.append(corners[(actual_index + 1) % 4].copy())

        return points

    def _get_coastline_points(
        self, entry: BoundingBoxIntersection, exit_int: BoundingBoxIntersection
    ) -> list[np.ndarray]:
        """Get coastline node coordinates between entry and exit."""
        points: list[np.ndarray] = []
        coastline = self._coastlines[entry.coastline_index]

        start_seg = entry.segment_index
        end_seg = exit_int.segment_index

        # Add nodes from `start_seg` + 1 to `end_seg` (inclusive).
        if start_seg < end_seg:
            points = [
                coastline[i].coordinates.copy()
                for i in range(start_seg + 1, end_seg + 1)
            ]
        else:
            # Coastline wraps around (cyclic).
            for i in range(start_seg + 1, len(coastline)):
                points.append(coastline[i].coordinates.copy())
            for i in range(end_seg + 1):
                points.append(coastline[i].coordinates.copy())

        return points

    def _handle_no_intersections(self) -> list[WaterPolygon]:
        """Handle case where no coastlines intersect the bounding box."""

        # If there are closed coastlines entirely inside, they are islands. The
        # bounding box itself might be entirely water or entirely land. For now,
        # return empty — more sophisticated detection could be added.
        return []
