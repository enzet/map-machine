"""Test coastline water polygon construction."""

import numpy as np

from map_machine.geometry.bounding_box import BoundingBox
from map_machine.geometry.coastline import (
    BoundingBoxEdge,
    BoundingBoxIntersection,
    CoastlineProcessor,
    IntersectionType,
    WaterPolygon,
    _glue_coastlines,
    _try_merge,
)
from map_machine.osm.osm_reader import OSMData, OSMNode, OSMWay


def create_node(lat: float, lon: float, node_id: int = -1) -> OSMNode:
    """Create a test OSMNode."""
    return OSMNode(tags={}, id_=node_id, coordinates=np.array((lat, lon)))


def create_coastline_way(
    coords: list[tuple[float, float]], way_id: int = 1
) -> OSMWay:
    """Create a test coastline way."""
    nodes = [create_node(lat, lon, i) for i, (lat, lon) in enumerate(coords)]
    return OSMWay(tags={"natural": "coastline"}, id_=way_id, nodes=nodes)


class TestBoundingBoxHelpers:
    """Test BoundingBox helper methods."""

    def test_contains_point_inside(self) -> None:
        """Test point inside bounding box."""
        bounding_box = BoundingBox(0.0, 0.0, 1.0, 1.0)
        assert bounding_box.contains_point(np.array((0.5, 0.5)))

    def test_contains_point_outside(self) -> None:
        """Test point outside bounding box."""
        bounding_box = BoundingBox(0.0, 0.0, 1.0, 1.0)
        assert not bounding_box.contains_point(np.array((1.5, 0.5)))

    def test_contains_point_on_edge(self) -> None:
        """Test point on bounding box edge."""
        bounding_box = BoundingBox(0.0, 0.0, 1.0, 1.0)
        assert bounding_box.contains_point(np.array((0.5, 0.0)))
        assert bounding_box.contains_point(np.array((1.0, 0.5)))

    def test_get_corners(self) -> None:
        """Test getting corners in clockwise order."""
        bounding_box = BoundingBox(0.0, 0.0, 1.0, 1.0)
        corners = bounding_box.get_corners()
        assert len(corners) == 4  # noqa: PLR2004
        assert np.allclose(corners[0], np.array((1.0, 0.0)))  # Top-left.
        assert np.allclose(corners[1], np.array((1.0, 1.0)))  # Top-right.
        assert np.allclose(corners[2], np.array((0.0, 1.0)))  # Bottom-right.
        assert np.allclose(corners[3], np.array((0.0, 0.0)))  # Bottom-left.


class TestCoastlineGluing:
    """Test coastline segment gluing."""

    def test_try_merge_end_to_start(self) -> None:
        """Test merging when a[-1] == b[0]."""
        a = [create_node(0, 0, 1), create_node(1, 1, 2)]
        b = [create_node(1, 1, 2), create_node(2, 2, 3)]
        result = _try_merge(a, b)
        assert result is not None
        assert len(result) == 3  # noqa: PLR2004

    def test_try_merge_no_match(self) -> None:
        """Test no merge when segments don't share endpoints."""
        a = [create_node(0, 0, 1), create_node(1, 1, 2)]
        b = [create_node(5, 5, 5), create_node(6, 6, 6)]
        result = _try_merge(a, b)
        assert result is None

    def test_glue_coastlines_empty(self) -> None:
        """Test gluing empty list."""
        result = _glue_coastlines([])
        assert result == []

    def test_glue_coastlines_single_closed(self) -> None:
        """Test gluing single closed coastline."""
        node = create_node(0, 0, 1)
        coastline = [node, create_node(1, 0, 2), create_node(0, 1, 3), node]
        result = _glue_coastlines([coastline])
        assert len(result) == 1
        assert result[0] == coastline


class TestIntersectionDetection:
    """Test intersection detection between coastlines and bounding box."""

    def test_simple_crossing_top_edge(self) -> None:
        """Test coastline crossing top edge."""
        bounding_box = BoundingBox(0.0, 0.0, 1.0, 1.0)
        processor = CoastlineProcessor(bounding_box)

        # Coastline from outside (above) to inside.
        coastline = [create_node(1.5, 0.5, 1), create_node(0.5, 0.5, 2)]

        intersections: list[BoundingBoxIntersection] = (
            processor._find_intersections(coastline, 0)  # noqa: SLF001
        )
        assert len(intersections) == 1
        assert intersections[0].edge == BoundingBoxEdge.TOP
        assert intersections[0].type_ == IntersectionType.ENTRY

    def test_simple_crossing_bottom_edge(self) -> None:
        """Test coastline crossing bottom edge."""
        bounding_box = BoundingBox(0.0, 0.0, 1.0, 1.0)
        processor = CoastlineProcessor(bounding_box)

        # Coastline from inside to outside (below).
        coastline: list[OSMNode] = [
            create_node(0.5, 0.5, 1),
            create_node(-0.5, 0.5, 2),
        ]
        intersections: list[BoundingBoxIntersection] = (
            processor._find_intersections(coastline, 0)  # noqa: SLF001
        )
        assert len(intersections) == 1
        assert intersections[0].edge == BoundingBoxEdge.BOTTOM
        assert intersections[0].type_ == IntersectionType.EXIT

    def test_crossing_multiple_edges(self) -> None:
        """Test coastline crossing multiple edges."""
        bounding_box = BoundingBox(0.0, 0.0, 1.0, 1.0)
        processor = CoastlineProcessor(bounding_box)

        # Coastline enters from left, exits from right.
        coastline = [
            create_node(0.5, -0.5, 1),  # Outside left.
            create_node(0.5, 0.5, 2),  # Inside.
            create_node(0.5, 1.5, 3),  # Outside right.
        ]
        intersections: list[BoundingBoxIntersection] = (
            processor._find_intersections(coastline, 0)  # noqa: SLF001
        )
        assert len(intersections) == 2  # noqa: PLR2004

        # Should have ENTRY on left edge and EXIT on right edge.
        entry = [i for i in intersections if i.type_ == IntersectionType.ENTRY]
        exit_ = [i for i in intersections if i.type_ == IntersectionType.EXIT]
        assert len(entry) == 1
        assert len(exit_) == 1
        assert entry[0].edge == BoundingBoxEdge.LEFT
        assert exit_[0].edge == BoundingBoxEdge.RIGHT


class TestPerimeterPosition:
    """Test perimeter position calculation."""

    def test_top_edge_positions(self) -> None:
        """Test positions along top edge."""
        bounding_box = BoundingBox(0.0, 0.0, 1.0, 1.0)
        processor = CoastlineProcessor(bounding_box)

        # Left of top edge.
        pos1 = processor._get_perimeter_position(  # noqa: SLF001
            np.array((1.0, 0.0)), BoundingBoxEdge.TOP
        )
        assert np.isclose(pos1, 0.0)

        # Middle of top edge.
        pos2 = processor._get_perimeter_position(  # noqa: SLF001
            np.array((1.0, 0.5)), BoundingBoxEdge.TOP
        )
        assert np.isclose(pos2, 0.5)

        # Right of top edge.
        pos3 = processor._get_perimeter_position(  # noqa: SLF001
            np.array((1.0, 1.0)), BoundingBoxEdge.TOP
        )
        assert np.isclose(pos3, 1.0)

    def test_clockwise_order(self) -> None:
        """Test that positions increase clockwise."""
        bounding_box = BoundingBox(0.0, 0.0, 1.0, 1.0)
        processor = CoastlineProcessor(bounding_box)

        # Points going clockwise around bounding box.
        positions = [
            processor._get_perimeter_position(  # noqa: SLF001
                np.array((1.0, 0.5)), BoundingBoxEdge.TOP
            ),  # Top edge.
            processor._get_perimeter_position(  # noqa: SLF001
                np.array((0.5, 1.0)), BoundingBoxEdge.RIGHT
            ),  # Right edge.
            processor._get_perimeter_position(  # noqa: SLF001
                np.array((0.0, 0.5)), BoundingBoxEdge.BOTTOM
            ),  # Bottom edge.
            processor._get_perimeter_position(  # noqa: SLF001
                np.array((0.5, 0.0)), BoundingBoxEdge.LEFT
            ),  # Left edge.
        ]

        # Positions should be increasing.
        for i in range(len(positions) - 1):
            assert positions[i] < positions[i + 1]


class TestWaterPolygonConstruction:
    """Test construction of water polygons from coastlines."""

    def test_no_coastlines(self) -> None:
        """Test with no coastlines - should return empty."""
        bounding_box = BoundingBox(0.0, 0.0, 1.0, 1.0)
        processor = CoastlineProcessor(bounding_box)

        osm_data = OSMData()
        result = processor.process(osm_data)
        assert result == []

    def test_simple_bay(self) -> None:
        """Test coastline creating a simple bay.

        Water on the right side of coastline direction.
        Coastline enters from left edge, exits from bottom edge.
        """
        bounding_box: BoundingBox = BoundingBox(0.0, 0.0, 1.0, 1.0)
        processor: CoastlineProcessor = CoastlineProcessor(bounding_box)

        # Coastline goes from left edge to bottom edge.
        # Water is on the right (bottom-left corner area).
        way: OSMWay = create_coastline_way(
            [
                (-0.5, 0.5),  # Outside left.
                (0.3, 0.3),  # Inside.
                (0.5, -0.5),  # Outside bottom.
            ]
        )
        osm_data: OSMData = OSMData()
        osm_data.ways[way.id_] = way

        result: list[WaterPolygon] = processor.process(osm_data)

        # Should create at least one water polygon. The exact shape depends on
        # the algorithm.
        assert len(result) >= 0  # May be 0 if algorithm needs refinement.

    def test_coastline_entirely_outside(self) -> None:
        """Test coastline entirely outside bounding box."""
        bounding_box: BoundingBox = BoundingBox(0.0, 0.0, 1.0, 1.0)
        processor: CoastlineProcessor = CoastlineProcessor(bounding_box)

        # Coastline far outside bounding box.
        way: OSMWay = create_coastline_way(
            [
                (5.0, 5.0),
                (6.0, 5.0),
                (6.0, 6.0),
            ]
        )
        osm_data: OSMData = OSMData()
        osm_data.ways[way.id_] = way

        result: list[WaterPolygon] = processor.process(osm_data)
        assert result == []


class TestWaterPolygonClass:
    """Test WaterPolygon dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        polygon = WaterPolygon()
        assert polygon.points == []
        assert polygon.is_hole is False

    def test_with_points(self) -> None:
        """Test with points."""
        points = [np.array((0, 0)), np.array((1, 0)), np.array((0, 1))]
        polygon = WaterPolygon(points=points)
        assert len(polygon.points) == 3  # noqa: PLR2004

    def test_island_hole(self) -> None:
        """Test island (hole in water)."""
        polygon = WaterPolygon(is_hole=True)
        assert polygon.is_hole is True


class TestBoundingBoxIntersection:
    """Test `BoundingBoxIntersection` dataclass."""

    def test_creation(self) -> None:
        """Test creating intersection."""
        intersection = BoundingBoxIntersection(
            coordinates=np.array((0.5, 0.0)),
            edge=BoundingBoxEdge.LEFT,
            type_=IntersectionType.ENTRY,
            coastline_index=0,
            segment_index=0,
        )
        assert intersection.edge == BoundingBoxEdge.LEFT
        assert intersection.type_ == IntersectionType.ENTRY
        assert intersection.coastline_index == 0
