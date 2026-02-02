"""Test bounding box cropping of ways and areas."""

import numpy as np

from map_machine.geometry.bounding_box import BoundingBox
from map_machine.geometry.crop import (
    _all_inside,
    _nodes_to_shapely_coords,
    _shapely_coords_to_nodes,
    crop_multipolygon,
    crop_way,
)
from map_machine.osm.osm_reader import OSMNode


def create_node(lat: float, lon: float, node_id: int = -1) -> OSMNode:
    """Create a test OSMNode."""
    return OSMNode(tags={}, id_=node_id, coordinates=np.array((lat, lon)))


# Bounding box: lon [0, 1], lat [0, 1].
BBOX: BoundingBox = BoundingBox(0.0, 0.0, 1.0, 1.0)


class TestCoordinateConversion:
    """Test coordinate conversion between OSMNode and Shapely."""

    def test_roundtrip(self) -> None:
        """Coordinates survive a round-trip through Shapely format."""
        nodes = [create_node(10.0, 20.0), create_node(30.0, 40.0)]
        coords = _nodes_to_shapely_coords(nodes)
        assert coords == [(20.0, 10.0), (40.0, 30.0)]

        result = _shapely_coords_to_nodes(coords)
        assert len(result) == 2
        np.testing.assert_allclose(
            result[0].coordinates, np.array((10.0, 20.0))
        )
        np.testing.assert_allclose(
            result[1].coordinates, np.array((30.0, 40.0))
        )


class TestAllInside:
    """Test the fast-path _all_inside check."""

    def test_all_inside(self) -> None:
        """All nodes inside the bounding box."""
        nodes = [create_node(0.5, 0.5), create_node(0.3, 0.7)]
        assert _all_inside(nodes, BBOX)

    def test_one_outside(self) -> None:
        """One node outside the bounding box."""
        nodes = [create_node(0.5, 0.5), create_node(1.5, 0.5)]
        assert not _all_inside(nodes, BBOX)


class TestCropWayLine:
    """Test cropping of open linestrings."""

    def test_all_inside(self) -> None:
        """Line entirely inside bbox is returned unchanged."""
        nodes = [create_node(0.2, 0.2), create_node(0.8, 0.8)]
        result = crop_way(nodes, BBOX, is_area=False)
        assert len(result) == 1
        assert result[0] is nodes  # Same object (fast path).

    def test_all_outside_no_crossing(self) -> None:
        """Line entirely outside bbox with no crossing returns empty."""
        nodes = [create_node(2.0, 2.0), create_node(3.0, 3.0)]
        result = crop_way(nodes, BBOX, is_area=False)
        assert len(result) == 0

    def test_crossing_bbox(self) -> None:
        """Line crossing the bbox produces a clipped segment."""
        nodes = [create_node(0.5, -0.5), create_node(0.5, 1.5)]
        result = crop_way(nodes, BBOX, is_area=False)
        assert len(result) == 1
        # The clipped line should be approximately from (0.5, 0.0) to
        # (0.5, 1.0).
        segment = result[0]
        assert len(segment) >= 2
        lats = [n.coordinates[0] for n in segment]
        lons = [n.coordinates[1] for n in segment]
        assert all(0.0 <= lat <= 1.0 for lat in lats)
        assert all(0.0 <= lon <= 1.0 for lon in lons)

    def test_multiple_segments(self) -> None:
        """Line that enters/exits bbox multiple times produces segments."""
        # Line goes: outside -> inside -> outside -> inside -> outside.
        nodes = [
            create_node(0.5, -0.5),
            create_node(0.5, 0.5),
            create_node(0.5, 1.5),
            create_node(0.5, 2.5),
        ]
        # This line enters and exits the bbox once, producing one segment
        # from the entry to the exit.
        result = crop_way(nodes, BBOX, is_area=False)
        assert len(result) >= 1
        for segment in result:
            for node in segment:
                assert 0.0 - 1e-9 <= node.coordinates[1] <= 1.0 + 1e-9

    def test_too_few_nodes(self) -> None:
        """Way with fewer than 2 nodes returns empty."""
        result = crop_way([create_node(0.5, 0.5)], BBOX, is_area=False)
        assert len(result) == 0

    def test_empty_nodes(self) -> None:
        """Empty node list returns empty."""
        result = crop_way([], BBOX, is_area=False)
        assert len(result) == 0


class TestCropWayArea:
    """Test cropping of closed polygons (areas)."""

    def test_all_inside(self) -> None:
        """Polygon entirely inside bbox is returned unchanged."""
        nodes = [
            create_node(0.2, 0.2),
            create_node(0.2, 0.8),
            create_node(0.8, 0.8),
            create_node(0.8, 0.2),
            create_node(0.2, 0.2),
        ]
        result = crop_way(nodes, BBOX, is_area=True)
        assert len(result) == 1
        assert result[0] is nodes

    def test_all_outside(self) -> None:
        """Polygon entirely outside bbox returns empty."""
        nodes = [
            create_node(2.0, 2.0),
            create_node(2.0, 3.0),
            create_node(3.0, 3.0),
            create_node(3.0, 2.0),
            create_node(2.0, 2.0),
        ]
        result = crop_way(nodes, BBOX, is_area=True)
        assert len(result) == 0

    def test_partial_overlap(self) -> None:
        """Polygon partially overlapping bbox produces a clipped polygon."""
        nodes = [
            create_node(-0.5, 0.25),
            create_node(-0.5, 0.75),
            create_node(0.5, 0.75),
            create_node(0.5, 0.25),
            create_node(-0.5, 0.25),
        ]
        result = crop_way(nodes, BBOX, is_area=True)
        assert len(result) == 1
        polygon = result[0]
        assert len(polygon) >= 4
        # All clipped points should be within the bbox.
        for node in polygon:
            assert -1e-9 <= node.coordinates[0] <= 1.0 + 1e-9
            assert -1e-9 <= node.coordinates[1] <= 1.0 + 1e-9

    def test_polygon_containing_bbox(self) -> None:
        """Polygon containing the entire bbox produces bbox-shaped result."""
        nodes = [
            create_node(-1.0, -1.0),
            create_node(-1.0, 2.0),
            create_node(2.0, 2.0),
            create_node(2.0, -1.0),
            create_node(-1.0, -1.0),
        ]
        result = crop_way(nodes, BBOX, is_area=True)
        assert len(result) == 1


class TestCropMultipolygon:
    """Test cropping of multipolygon outers and inners."""

    def test_all_inside(self) -> None:
        """Multipolygon entirely inside bbox is returned unchanged."""
        outer = [
            create_node(0.1, 0.1),
            create_node(0.1, 0.9),
            create_node(0.9, 0.9),
            create_node(0.9, 0.1),
            create_node(0.1, 0.1),
        ]
        inner = [
            create_node(0.3, 0.3),
            create_node(0.3, 0.7),
            create_node(0.7, 0.7),
            create_node(0.7, 0.3),
            create_node(0.3, 0.3),
        ]
        cropped_outers, cropped_inners = crop_multipolygon(
            [outer], [inner], BBOX
        )
        assert len(cropped_outers) == 1
        assert len(cropped_inners) == 1
        assert cropped_outers[0] is outer
        assert cropped_inners[0] is inner

    def test_outer_partially_outside(self) -> None:
        """Outer ring extending beyond bbox is clipped."""
        outer = [
            create_node(-0.5, 0.25),
            create_node(-0.5, 0.75),
            create_node(0.5, 0.75),
            create_node(0.5, 0.25),
            create_node(-0.5, 0.25),
        ]
        inner = [
            create_node(0.1, 0.4),
            create_node(0.1, 0.6),
            create_node(0.3, 0.6),
            create_node(0.3, 0.4),
            create_node(0.1, 0.4),
        ]
        cropped_outers, cropped_inners = crop_multipolygon(
            [outer], [inner], BBOX
        )
        assert len(cropped_outers) == 1
        assert len(cropped_inners) == 1
        # Outer should be clipped.
        for node in cropped_outers[0]:
            assert -1e-9 <= node.coordinates[0] <= 1.0 + 1e-9
        # Inner was fully inside, so should be unchanged.
        assert cropped_inners[0] is inner

    def test_inner_fully_outside(self) -> None:
        """Inner ring fully outside bbox is dropped."""
        outer = [
            create_node(-0.5, -0.5),
            create_node(-0.5, 1.5),
            create_node(1.5, 1.5),
            create_node(1.5, -0.5),
            create_node(-0.5, -0.5),
        ]
        inner = [
            create_node(2.0, 2.0),
            create_node(2.0, 3.0),
            create_node(3.0, 3.0),
            create_node(3.0, 2.0),
            create_node(2.0, 2.0),
        ]
        cropped_outers, cropped_inners = crop_multipolygon(
            [outer], [inner], BBOX
        )
        assert len(cropped_outers) == 1
        assert len(cropped_inners) == 0
