"""Water polygon construction for partial map data.

This module handles two cases of incomplete water boundaries:

1. OSM coastlines (`natural=coastline`). Ways where land is on the left and
   water is on the right. When downloading partial data, coastlines appear as
   incomplete segments.

2. Water multipolygon relations (`natural=water`, `water=lake`, etc.). When
   downloading partial data, only some member ways of the relation may be
   present, resulting in incomplete boundaries.

Both cases are handled by finding intersections with the bounding box and
connecting segments along the bounding box edges to form closed water polygons.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from map_machine.geometry.bounding_box import BoundingBox
    from map_machine.osm.osm_reader import OSMData, OSMNode, OSMRelation

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

    relation_id: int | None = None
    """Original relation id if this polygon came from a water relation."""


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


def _compute_signed_area(points: list[np.ndarray]) -> float:
    """Compute signed area of a polygon using the shoelace formula.

    Points are (latitude, longitude), treated as (y, x).

    :return: positive for counter-clockwise winding, negative for clockwise
    """
    area: float = 0.0
    size: int = len(points)
    for i in range(size):
        j = (i + 1) % size
        # Shoelace: sum of (x_i * y_{i + 1} - x_{i + 1} * y_i),
        # where x = longitude (index 1), y = latitude (index 0).
        area += points[i][1] * points[j][0] - points[j][1] * points[i][0]
    return area / 2.0


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


def segment_bounding_box_edge_intersection(
    bounding_box: BoundingBox,
    point_1: np.ndarray,
    point_2: np.ndarray,
    edge: BoundingBoxEdge,
) -> np.ndarray | None:
    """Check if segment intersects bounding box edge.

    Uses parametric line intersection.

    :param bounding_box: the bounding box
    :param point_1: first point of segment (latitude, longitude)
    :param point_2: second point of segment (latitude, longitude)
    :param edge: which edge of the bounding box to check
    :return: intersection point or None
    """
    # Get edge endpoints (latitude, longitude).
    corners: list[np.ndarray] = bounding_box.get_corners()
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


def get_bounding_box_perimeter_position(
    bounding_box: BoundingBox, point: np.ndarray, edge: BoundingBoxEdge
) -> float:
    """Get position along bounding box perimeter.

    :param bounding_box: the bounding box
    :param point: point on the edge (latitude, longitude)
    :param edge: which edge the point is on
    :return: position from 0 to 4, clockwise from top-left
    """
    lat, lon = point[0], point[1]

    if edge == BoundingBoxEdge.TOP:
        # Position along top edge (left to right).
        t = (lon - bounding_box.left) / (bounding_box.right - bounding_box.left)
        return 0.0 + t
    if edge == BoundingBoxEdge.RIGHT:
        # Position along right edge (top to bottom).
        t = (bounding_box.top - lat) / (bounding_box.top - bounding_box.bottom)
        return 1.0 + t
    if edge == BoundingBoxEdge.BOTTOM:
        # Position along bottom edge (right to left).
        t = (bounding_box.right - lon) / (
            bounding_box.right - bounding_box.left
        )
        return 2.0 + t
    # Position along left edge (bottom to top).
    t = (lat - bounding_box.bottom) / (bounding_box.top - bounding_box.bottom)
    return 3.0 + t


def find_bounding_box_intersections(
    bounding_box: BoundingBox,
    boundary: list[OSMNode],
    boundary_index: int = 0,
) -> list[BoundingBoxIntersection]:
    """Find all points where a boundary crosses bounding box edges.

    :param bounding_box: the bounding box
    :param boundary: list of OSM nodes forming the boundary
    :param boundary_index: index to store in the intersection (for tracking)
    :return: list of intersection points with entry/exit classification
    """
    intersections: list[BoundingBoxIntersection] = []

    for index in range(len(boundary) - 1):
        point_1: np.ndarray = boundary[index].coordinates
        point_2: np.ndarray = boundary[index + 1].coordinates

        # Check intersection with each bounding box edge.
        for edge in BoundingBoxEdge:
            intersection = segment_bounding_box_edge_intersection(
                bounding_box, point_1, point_2, edge
            )
            if intersection is not None:
                # Determine if entering or exiting.
                inside_point_1: bool = bounding_box.contains_point(point_1)
                inside_point_2: bool = bounding_box.contains_point(point_2)

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
                        coastline_index=boundary_index,
                        segment_index=index,
                    )
                )

    return intersections


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
            intersections = find_bounding_box_intersections(
                self.bounding_box, coastline, coast_index
            )
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

    def _sort_intersections_clockwise(self) -> None:
        """Sort intersection points by position along bounding box perimeter."""

        # Calculate perimeter position for each intersection. Clockwise from
        # top-left.
        for intersection in self._intersections:
            intersection.perimeter_position = (
                get_bounding_box_perimeter_position(
                    self.bounding_box,
                    intersection.coordinates,
                    intersection.edge,
                )
            )

        self._intersections.sort(key=lambda x: x.perimeter_position)

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
        corners = self.bounding_box.get_corners()

        # Handle wrap-around.
        if to_position < from_position:
            to_position += 4.0

        # Collect corners between `from_position` and `to_position` with
        # their adjusted positions, then sort to ensure correct order when
        # wrapping around the perimeter.
        corner_entries: list[tuple[float, np.ndarray]] = []
        for corner_index in range(4):
            corner_position = float(corner_index + 1)  # 1, 2, 3, 4.
            if corner_position <= from_position:
                corner_position += 4.0
            if from_position < corner_position < to_position:
                corner_entries.append(
                    (corner_position, corners[(corner_index + 1) % 4].copy())
                )

        corner_entries.sort(key=lambda entry: entry[0])
        return [corner for _, corner in corner_entries]

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


class WaterRelationProcessor:
    """Processes incomplete water multipolygon relations."""

    def __init__(self, bounding_box: BoundingBox) -> None:
        self.bounding_box: BoundingBox = bounding_box
        self._boundaries: list[list[OSMNode]] = []
        self._intersections: list[BoundingBoxIntersection] = []

    def process(self, osm_data: OSMData) -> tuple[list[WaterPolygon], set[int]]:
        """Process incomplete water relations.

        :param osm_data: OSM data containing relations and ways
        :return: tuple of (water polygons, set of processed relation ids)
        """
        water_polygons: list[WaterPolygon] = []
        processed_relation_ids: set[int] = set()

        for relation in osm_data.relations.values():
            if not self._is_water_relation(relation):
                continue

            # Get outer ways that are present in the data.
            outer_ways = []
            missing_ways = False
            for member in relation.members or []:
                if member.type_ == "way" and member.role == "outer":
                    if member.ref in osm_data.ways:
                        outer_ways.append(osm_data.ways[member.ref])
                    else:
                        missing_ways = True

            if not outer_ways:
                continue

            # Glue the outer ways together.
            glued_outers: list[list[OSMNode]] = _glue_coastlines(
                [way.nodes for way in outer_ways]
            )

            # Check if any outer boundary is incomplete (not closed).
            has_incomplete = any(
                boundary[0] != boundary[-1] for boundary in glued_outers
            )

            if not has_incomplete and not missing_ways:
                # Complete relation, let normal processing handle it.
                continue

            # Process incomplete boundaries.
            for boundary in glued_outers:
                if boundary[0] == boundary[-1]:
                    # This boundary is complete, add as-is.
                    polygon = WaterPolygon(relation_id=relation.id_)
                    for node in boundary:
                        polygon.points.append(node.coordinates.copy())
                    water_polygons.append(polygon)
                else:
                    # Incomplete boundary, complete with bounding box.
                    completed = self._complete_boundary(boundary)
                    if completed:
                        completed.relation_id = relation.id_

                        water_polygons.append(completed)

            processed_relation_ids.add(relation.id_)

        return water_polygons, processed_relation_ids

    def _is_water_relation(self, relation: OSMRelation) -> bool:
        """Check if relation is a water body multipolygon."""
        tags = relation.tags
        if tags.get("type") != "multipolygon":
            return False

        # Check for water-related tags.
        if tags.get("natural") == "water":
            return True
        if tags.get("water") in (
            "lagoon",
            "lake",
            "oxbow",
            "rapids",
            "river",
            "stream",
            "stream_pool",
        ):
            return True
        return tags.get("landuse") == "reservoir"

    def _complete_boundary(
        self, boundary: list[OSMNode]
    ) -> WaterPolygon | None:
        """Complete an incomplete water boundary using bounding box edges.

        For water relations, water is inside the polygon. We determine the
        correct bounding box path by checking which direction produces a
        polygon with the correct winding (counter-clockwise = water inside).

        The boundary may cross the bounding box multiple times, creating
        multiple entry-exit pairs. Each pair defines an interior segment.
        We connect these segments via bounding box edges.
        """
        if len(boundary) < 2:  # noqa: PLR2004
            return None

        # Find intersections with bounding box.
        intersections = find_bounding_box_intersections(
            self.bounding_box, boundary
        )

        if len(intersections) < 2:  # noqa: PLR2004
            # Boundary doesn't properly cross bounding box, skip.
            return None

        # Sort intersections by their position in the boundary.
        intersections.sort(key=lambda x: x.segment_index)

        # Compute perimeter positions for bounding box path construction.
        for intersection in intersections:
            intersection.perimeter_position = (
                get_bounding_box_perimeter_position(
                    self.bounding_box,
                    intersection.coordinates,
                    intersection.edge,
                )
            )

        # Build entry-exit pairs from sorted intersections.
        pairs: list[
            tuple[BoundingBoxIntersection, BoundingBoxIntersection]
        ] = []
        index = 0
        while index < len(intersections):
            if intersections[index].type_ == IntersectionType.ENTRY:
                # Find next exit after this entry.
                for j in range(index + 1, len(intersections)):
                    if intersections[j].type_ == IntersectionType.EXIT:
                        pairs.append((intersections[index], intersections[j]))
                        index = j + 1
                        break
                else:
                    index += 1
            else:
                index += 1

        if not pairs:
            return None

        # Collect the boundary-only points (without any bounding box path)
        # to determine the local winding direction of the boundary segment.
        boundary_only_points: list[np.ndarray] = []

        # Build polygon points using both clockwise and counter-clockwise
        # bounding box paths, then pick the correct one based on signed area.
        cw_points: list[np.ndarray] = []
        ccw_points: list[np.ndarray] = []

        for pair_index, (entry, exit_) in enumerate(pairs):
            # Add entry point.
            cw_points.append(entry.coordinates.copy())
            ccw_points.append(entry.coordinates.copy())
            boundary_only_points.append(entry.coordinates.copy())

            # Add interior boundary points between entry and exit.
            for node_index in range(
                entry.segment_index + 1, exit_.segment_index + 1
            ):
                if node_index < len(boundary):
                    coord = boundary[node_index].coordinates.copy()
                    cw_points.append(coord)
                    ccw_points.append(coord.copy())
                    boundary_only_points.append(coord.copy())

            # Add exit point.
            cw_points.append(exit_.coordinates.copy())
            ccw_points.append(exit_.coordinates.copy())
            boundary_only_points.append(exit_.coordinates.copy())

            # Add bounding box path to next entry (wrapping to first pair).
            next_entry = pairs[(pair_index + 1) % len(pairs)][0]

            cw_path = self._get_clockwise_bounding_box_path(
                exit_.coordinates,
                exit_.edge,
                next_entry.coordinates,
                next_entry.edge,
            )
            ccw_path = self._get_ccw_bounding_box_path(
                exit_.coordinates,
                exit_.edge,
                next_entry.coordinates,
                next_entry.edge,
            )

            cw_points.extend(cw_path)
            ccw_points.extend(ccw_path)

        # Determine the correct bounding box path direction.
        #
        # The boundary segment is part of the outer ring of a water body.
        # When we close just the boundary segment (without a bounding box
        # path), its signed area tells us the local winding direction.
        #
        # The correct water polygon has the *opposite* winding from the
        # boundary segment alone: the boundary traces one portion of the
        # ring in one direction, and the bounding box path completes the
        # polygon by going around the water area in the other direction.
        boundary_area = _compute_signed_area(boundary_only_points)
        cw_area = _compute_signed_area(cw_points)

        if boundary_area * cw_area < 0:
            # Opposite signs: CW polygon is the water polygon.
            polygon_points = cw_points
        else:
            # Same signs: CCW polygon is the water polygon.
            polygon_points = ccw_points

        polygon = WaterPolygon()
        polygon.points = polygon_points

        # Close the polygon.
        if polygon.points and not np.allclose(
            polygon.points[0], polygon.points[-1]
        ):
            polygon.points.append(polygon.points[0].copy())

        if len(polygon.points) < 4:  # noqa: PLR2004
            return None

        return polygon

    def _get_clockwise_bounding_box_path(
        self,
        from_point: np.ndarray,
        from_edge: BoundingBoxEdge,
        to_point: np.ndarray,
        to_edge: BoundingBoxEdge,
    ) -> list[np.ndarray]:
        """Get bounding box corners going clockwise from exit to entry."""
        from_position = get_bounding_box_perimeter_position(
            self.bounding_box, from_point, from_edge
        )
        to_position = get_bounding_box_perimeter_position(
            self.bounding_box, to_point, to_edge
        )
        corners = self.bounding_box.get_corners()

        target_position = (
            to_position if to_position > from_position else to_position + 4.0
        )

        corner_entries: list[tuple[float, np.ndarray]] = []
        for corner_index in range(4):
            corner_position = float(corner_index + 1)
            if corner_position <= from_position:
                corner_position += 4.0
            if from_position < corner_position < target_position:
                corner_entries.append(
                    (corner_position, corners[(corner_index + 1) % 4].copy())
                )
        corner_entries.sort(key=lambda entry: entry[0])
        return [corner for _, corner in corner_entries]

    def _get_ccw_bounding_box_path(
        self,
        from_point: np.ndarray,
        from_edge: BoundingBoxEdge,
        to_point: np.ndarray,
        to_edge: BoundingBoxEdge,
    ) -> list[np.ndarray]:
        """Get bounding box corners going counter-clockwise from exit."""
        from_position = get_bounding_box_perimeter_position(
            self.bounding_box, from_point, from_edge
        )
        to_position = get_bounding_box_perimeter_position(
            self.bounding_box, to_point, to_edge
        )
        corners = self.bounding_box.get_corners()

        target_position = (
            to_position if to_position < from_position else to_position - 4.0
        )

        corner_entries: list[tuple[float, np.ndarray]] = []
        for corner_index in range(3, -1, -1):
            corner_position = float(corner_index + 1)
            if corner_position >= from_position:
                corner_position -= 4.0
            if target_position < corner_position < from_position:
                corner_entries.append(
                    (corner_position, corners[(corner_index + 1) % 4].copy())
                )
        # Sort descending for counter-clockwise traversal.
        corner_entries.sort(key=lambda entry: entry[0], reverse=True)
        return [corner for _, corner in corner_entries]
