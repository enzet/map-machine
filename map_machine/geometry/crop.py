"""Crop geometries to bounding box using Shapely."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPolygon,
    Polygon,
    box,
)
from shapely.validation import make_valid

from map_machine.osm.osm_reader import OSMNode

if TYPE_CHECKING:
    from map_machine.geometry.bounding_box import BoundingBox

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

logger: logging.Logger = logging.getLogger(__name__)


def _nodes_to_shapely_coords(
    nodes: list[OSMNode],
) -> list[tuple[float, float]]:
    """Convert OSMNode list to Shapely (x, y) = (lon, lat) tuples."""
    return [
        (float(node.coordinates[1]), float(node.coordinates[0]))
        for node in nodes
    ]


def _shapely_coords_to_nodes(
    coordinates: list[tuple[float, float]],
) -> list[OSMNode]:
    """Convert Shapely coordinate sequence to synthetic OSMNodes.

    Shapely coords are (lon, lat); OSMNode takes (lat, lon).
    """
    return [
        OSMNode.from_coordinates(np.array((latitude, longitude)))
        for longitude, latitude in coordinates
    ]


def _all_inside(nodes: list[OSMNode], bounding_box: BoundingBox) -> bool:
    """Return True if all nodes are inside the bounding box."""
    return all(bounding_box.contains_point(node.coordinates) for node in nodes)


def _make_bbox_polygon(bounding_box: BoundingBox) -> Polygon:
    """Create a Shapely box polygon from a BoundingBox."""
    return box(
        bounding_box.left,
        bounding_box.bottom,
        bounding_box.right,
        bounding_box.top,
    )


def _extract_polygons(
    geometry: Polygon | MultiPolygon | GeometryCollection,
) -> list[list[OSMNode]]:
    """Extract polygon node lists from a Shapely geometry result."""
    result: list[list[OSMNode]] = []

    if geometry.is_empty:
        return result

    if isinstance(geometry, Polygon):
        nodes = _shapely_coords_to_nodes(geometry.exterior.coords)
        if len(nodes) >= 3:
            result.append(nodes)
    elif isinstance(geometry, MultiPolygon):
        for polygon in geometry.geoms:
            nodes = _shapely_coords_to_nodes(polygon.exterior.coords)
            if len(nodes) >= 3:
                result.append(nodes)
    elif isinstance(geometry, GeometryCollection):
        for geom in geometry.geoms:
            if isinstance(geom, Polygon) and not geom.is_empty:
                nodes = _shapely_coords_to_nodes(geom.exterior.coords)
                if len(nodes) >= 3:
                    result.append(nodes)

    return result


def _extract_linestrings(
    geometry: LineString | MultiLineString | GeometryCollection,
) -> list[list[OSMNode]]:
    """Extract linestring node lists from a Shapely geometry result."""
    result: list[list[OSMNode]] = []

    if geometry.is_empty:
        return result

    if isinstance(geometry, LineString):
        nodes = _shapely_coords_to_nodes(geometry.coords)
        if len(nodes) >= 2:
            result.append(nodes)
    elif isinstance(geometry, MultiLineString):
        for line in geometry.geoms:
            nodes = _shapely_coords_to_nodes(line.coords)
            if len(nodes) >= 2:
                result.append(nodes)
    elif isinstance(geometry, GeometryCollection):
        for geom in geometry.geoms:
            if isinstance(geom, LineString) and not geom.is_empty:
                nodes = _shapely_coords_to_nodes(geom.coords)
                if len(nodes) >= 2:
                    result.append(nodes)

    return result


def crop_way(
    nodes: list[OSMNode],
    bounding_box: BoundingBox,
    *,
    is_area: bool,
    bbox_polygon: Polygon | None = None,
) -> list[list[OSMNode]]:
    """Crop a way to the bounding box.

    :param nodes: way nodes
    :param bounding_box: clipping rectangle
    :param is_area: if True, treat as closed polygon; otherwise, linestring
    :param bbox_polygon: pre-built Shapely bbox polygon (optimization)
    :return: list of node lists (may be empty, one, or multiple segments)
    """
    if len(nodes) < 2:
        return []

    if _all_inside(nodes, bounding_box):
        return [nodes]

    if bbox_polygon is None:
        bbox_polygon = _make_bbox_polygon(bounding_box)

    coords = _nodes_to_shapely_coords(nodes)

    if is_area and len(coords) >= 4:
        return _crop_polygon(coords, bbox_polygon)
    return _crop_linestring(coords, bbox_polygon)


def _crop_polygon(
    coords: list[tuple[float, float]],
    bbox_polygon: Polygon,
) -> list[list[OSMNode]]:
    """Clip a polygon to the bounding box."""
    try:
        shape = Polygon(coords)
        if not shape.is_valid:
            shape = make_valid(shape)
            if isinstance(shape, GeometryCollection | MultiPolygon):
                # `make_valid`` may split into multiple geometries.
                results: list[list[OSMNode]] = []
                for geom in shape.geoms:
                    if isinstance(geom, Polygon) and not geom.is_empty:
                        clipped = geom.intersection(bbox_polygon)
                        results.extend(_extract_polygons(clipped))
                return results
            if not isinstance(shape, Polygon):
                return []
        clipped = shape.intersection(bbox_polygon)
    except Exception:  # noqa: BLE001
        logger.debug("Failed to crop polygon, using original geometry.")
        return [_shapely_coords_to_nodes(coords)]

    return _extract_polygons(clipped)


def _crop_linestring(
    coords: list[tuple[float, float]],
    bbox_polygon: Polygon,
) -> list[list[OSMNode]]:
    """Clip a linestring to the bounding box."""
    try:
        shape = LineString(coords)
        clipped = shape.intersection(bbox_polygon)
    except Exception:  # noqa: BLE001
        logger.debug("Failed to crop linestring, using original geometry.")
        return [_shapely_coords_to_nodes(coords)]

    return _extract_linestrings(clipped)


def crop_multipolygon(
    outers: list[list[OSMNode]],
    inners: list[list[OSMNode]],
    bounding_box: BoundingBox,
    bbox_polygon: Polygon | None = None,
) -> tuple[list[list[OSMNode]], list[list[OSMNode]]]:
    """Crop a multipolygon's outers and inners to the bounding box.

    Crops each outer and inner ring independently. This is correct because
    `(outer - inner) ∩ bbox = (outer ∩ bbox) - (inner ∩ bbox)`.

    :param outers: outer boundary rings
    :param inners: inner boundary rings (holes)
    :param bounding_box: clipping rectangle
    :param bbox_polygon: pre-built Shapely bbox polygon (optimization)
    :return: (cropped_outers, cropped_inners)
    """
    if bbox_polygon is None:
        bbox_polygon = _make_bbox_polygon(bounding_box)

    cropped_outers: list[list[OSMNode]] = []
    for outer_nodes in outers:
        if len(outer_nodes) >= 4:
            cropped = crop_way(
                outer_nodes,
                bounding_box,
                is_area=True,
                bbox_polygon=bbox_polygon,
            )
            cropped_outers.extend(cropped)
        else:
            cropped_outers.append(outer_nodes)

    cropped_inners: list[list[OSMNode]] = []
    for inner_nodes in inners:
        if len(inner_nodes) >= 4:
            cropped = crop_way(
                inner_nodes,
                bounding_box,
                is_area=True,
                bbox_polygon=bbox_polygon,
            )
            cropped_inners.extend(cropped)
        else:
            cropped_inners.append(inner_nodes)

    return cropped_outers, cropped_inners
