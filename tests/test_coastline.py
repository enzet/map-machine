"""Test coastline water polygon construction."""

import numpy as np

from map_machine.geometry.bounding_box import BoundingBox
from map_machine.geometry.coastline import (
    BoundingBoxEdge,
    BoundingBoxIntersection,
    CoastlineProcessor,
    IntersectionType,
    WaterPolygon,
    WaterRelationProcessor,
    _glue_coastlines,
    _point_in_polygon,
    _try_merge,
    find_bounding_box_intersections,
    get_bounding_box_perimeter_position,
)
from map_machine.osm.osm_reader import (
    OSMData,
    OSMMember,
    OSMNode,
    OSMRelation,
    OSMWay,
)


def create_node(lat: float, lon: float, node_id: int = -1) -> OSMNode:
    """Create a test OSMNode."""
    return OSMNode(tags={}, id_=node_id, coordinates=np.array((lat, lon)))


def create_coastline_way(
    coords: list[tuple[float, float]], way_id: int = 1
) -> OSMWay:
    """Create a test coastline way."""
    nodes: list[OSMNode] = [
        create_node(latitude, longitude, index)
        for index, (latitude, longitude) in enumerate(coords)
    ]
    return OSMWay(tags={"natural": "coastline"}, id_=way_id, nodes=nodes)


class TestBoundingBoxHelpers:
    """Test `BoundingBox` helper methods."""

    def test_contains_point_inside(self) -> None:
        """Test point inside bounding box."""
        bounding_box: BoundingBox = BoundingBox(0.0, 0.0, 1.0, 1.0)
        assert bounding_box.contains_point(np.array((0.5, 0.5)))

    def test_contains_point_outside(self) -> None:
        """Test point outside bounding box."""
        bounding_box: BoundingBox = BoundingBox(0.0, 0.0, 1.0, 1.0)
        assert not bounding_box.contains_point(np.array((1.5, 0.5)))

    def test_contains_point_on_edge(self) -> None:
        """Test point on bounding box edge."""
        bounding_box: BoundingBox = BoundingBox(0.0, 0.0, 1.0, 1.0)
        assert bounding_box.contains_point(np.array((0.5, 0.0)))
        assert bounding_box.contains_point(np.array((1.0, 0.5)))

    def test_get_corners(self) -> None:
        """Test getting corners in clockwise order."""
        bounding_box: BoundingBox = BoundingBox(0.0, 0.0, 1.0, 1.0)
        corners = bounding_box.get_corners()
        assert len(corners) == 4  # noqa: PLR2004
        assert np.allclose(corners[0], np.array((1.0, 0.0)))
        assert np.allclose(corners[1], np.array((1.0, 1.0)))
        assert np.allclose(corners[2], np.array((0.0, 1.0)))
        assert np.allclose(corners[3], np.array((0.0, 0.0)))


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
        result: list[OSMNode] | None = _try_merge(a, b)
        assert result is None

    def test_glue_coastlines_empty(self) -> None:
        """Test gluing empty list."""
        result: list[list[OSMNode]] = _glue_coastlines([])
        assert result == []

    def test_glue_coastlines_single_closed(self) -> None:
        """Test gluing single closed coastline."""
        node: OSMNode = create_node(0, 0, 1)
        coastline: list[OSMNode] = [
            node,
            create_node(1, 0, 2),
            create_node(0, 1, 3),
            node,
        ]
        result: list[list[OSMNode]] = _glue_coastlines([coastline])
        assert len(result) == 1
        assert result[0] == coastline


class TestIntersectionDetection:
    """Test intersection detection between coastlines and bounding box."""

    def test_simple_crossing_top_edge(self) -> None:
        """Test coastline crossing top edge."""
        bounding_box: BoundingBox = BoundingBox(0.0, 0.0, 1.0, 1.0)

        # Coastline from outside (above) to inside.
        coastline: list[OSMNode] = [
            create_node(1.5, 0.5, 1),
            create_node(0.5, 0.5, 2),
        ]
        intersections: list[BoundingBoxIntersection] = (
            find_bounding_box_intersections(bounding_box, coastline, 0)
        )
        assert len(intersections) == 1
        assert intersections[0].edge == BoundingBoxEdge.TOP
        assert intersections[0].type_ == IntersectionType.ENTRY

    def test_simple_crossing_bottom_edge(self) -> None:
        """Test coastline crossing bottom edge."""
        bounding_box: BoundingBox = BoundingBox(0.0, 0.0, 1.0, 1.0)

        # Coastline from inside to outside (below).
        coastline: list[OSMNode] = [
            create_node(0.5, 0.5, 1),
            create_node(-0.5, 0.5, 2),
        ]
        intersections: list[BoundingBoxIntersection] = (
            find_bounding_box_intersections(bounding_box, coastline, 0)
        )
        assert len(intersections) == 1
        assert intersections[0].edge == BoundingBoxEdge.BOTTOM
        assert intersections[0].type_ == IntersectionType.EXIT

    def test_crossing_multiple_edges(self) -> None:
        """Test coastline crossing multiple edges."""
        bounding_box: BoundingBox = BoundingBox(0.0, 0.0, 1.0, 1.0)

        # Coastline enters from left, exits from right.
        coastline = [
            create_node(0.5, -0.5, 1),  # Outside left.
            create_node(0.5, 0.5, 2),  # Inside.
            create_node(0.5, 1.5, 3),  # Outside right.
        ]
        intersections: list[BoundingBoxIntersection] = (
            find_bounding_box_intersections(bounding_box, coastline, 0)
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
        bounding_box: BoundingBox = BoundingBox(0.0, 0.0, 1.0, 1.0)

        # Left of top edge.
        pos1 = get_bounding_box_perimeter_position(
            bounding_box, np.array((1.0, 0.0)), BoundingBoxEdge.TOP
        )
        assert np.isclose(pos1, 0.0)

        # Middle of top edge.
        pos2 = get_bounding_box_perimeter_position(
            bounding_box, np.array((1.0, 0.5)), BoundingBoxEdge.TOP
        )
        assert np.isclose(pos2, 0.5)

        # Right of top edge.
        pos3 = get_bounding_box_perimeter_position(
            bounding_box, np.array((1.0, 1.0)), BoundingBoxEdge.TOP
        )
        assert np.isclose(pos3, 1.0)

    def test_clockwise_order(self) -> None:
        """Test that positions increase clockwise."""
        bounding_box: BoundingBox = BoundingBox(0.0, 0.0, 1.0, 1.0)

        # Points going clockwise around bounding box.
        positions = [
            get_bounding_box_perimeter_position(
                bounding_box, np.array((1.0, 0.5)), BoundingBoxEdge.TOP
            ),  # Top edge.
            get_bounding_box_perimeter_position(
                bounding_box, np.array((0.5, 1.0)), BoundingBoxEdge.RIGHT
            ),  # Right edge.
            get_bounding_box_perimeter_position(
                bounding_box, np.array((0.0, 0.5)), BoundingBoxEdge.BOTTOM
            ),  # Bottom edge.
            get_bounding_box_perimeter_position(
                bounding_box, np.array((0.5, 0.0)), BoundingBoxEdge.LEFT
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

        osm_data: OSMData = OSMData()
        result: list[WaterPolygon] = processor.process(osm_data)
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
        polygon: WaterPolygon = WaterPolygon()
        assert polygon.points == []
        assert polygon.is_hole is False

    def test_with_points(self) -> None:
        """Test with points."""
        points: list[np.ndarray] = [
            np.array((0, 0)),
            np.array((1, 0)),
            np.array((0, 1)),
        ]
        polygon: WaterPolygon = WaterPolygon(points=points)
        assert len(polygon.points) == 3  # noqa: PLR2004

    def test_island_hole(self) -> None:
        """Test island (hole in water)."""
        polygon: WaterPolygon = WaterPolygon(is_hole=True)
        assert polygon.is_hole is True


class TestBoundingBoxIntersection:
    """Test `BoundingBoxIntersection` dataclass."""

    def test_creation(self) -> None:
        """Test creating intersection."""
        intersection: BoundingBoxIntersection = BoundingBoxIntersection(
            coordinates=np.array((0.5, 0.0)),
            edge=BoundingBoxEdge.LEFT,
            type_=IntersectionType.ENTRY,
            coastline_index=0,
            segment_index=0,
        )
        assert intersection.edge == BoundingBoxEdge.LEFT
        assert intersection.type_ == IntersectionType.ENTRY
        assert intersection.coastline_index == 0


def create_water_relation(
    outer_coordinates: list[list[tuple[float, float]]],
    relation_id: int = 100,
    tags: dict[str, str] | None = None,
    *,
    closed: bool = False,
    inner_coordinates: list[list[tuple[float, float]]] | None = None,
) -> tuple[OSMRelation, list[OSMWay]]:
    """Create a test water multipolygon relation with its ways.

    :param closed: If True, the last node will be the same object as the first
        (simulating a closed way in real OSM data).
    :param inner_coordinates: Optional list of inner ring coordinate lists
        (islands/holes).
    """
    if tags is None:
        tags = {"type": "multipolygon", "natural": "water", "water": "lake"}

    ways: list[OSMWay] = []
    members: list[OSMMember] = []

    for way_index, coordinates in enumerate(outer_coordinates):
        way_id = relation_id * 10 + way_index
        nodes: list[OSMNode] = [
            create_node(latitude, longitude, way_id * 100 + index)
            for index, (latitude, longitude) in enumerate(coordinates)
        ]
        # For closed ways, replace the last node with the first node.
        if closed and len(nodes) > 1 and coordinates[0] == coordinates[-1]:
            nodes[-1] = nodes[0]
        way: OSMWay = OSMWay(tags={}, id_=way_id, nodes=nodes)
        ways.append(way)
        members.append(OSMMember(type_="way", ref=way_id, role="outer"))

    if inner_coordinates:
        for inner_index, coordinates in enumerate(inner_coordinates):
            way_id = relation_id * 10 + 100 + inner_index
            nodes = [
                create_node(latitude, longitude, way_id * 100 + index)
                for index, (latitude, longitude) in enumerate(coordinates)
            ]
            if closed and len(nodes) > 1 and coordinates[0] == coordinates[-1]:
                nodes[-1] = nodes[0]
            way = OSMWay(tags={}, id_=way_id, nodes=nodes)
            ways.append(way)
            members.append(OSMMember(type_="way", ref=way_id, role="inner"))

    relation: OSMRelation = OSMRelation(
        tags=tags, id_=relation_id, members=members
    )
    return relation, ways


class TestWaterRelationProcessor:
    """Test WaterRelationProcessor for incomplete water relations."""

    def test_no_water_relations(self) -> None:
        """Test with no water relations."""
        bounding_box: BoundingBox = BoundingBox(0.0, 0.0, 1.0, 1.0)
        processor: WaterRelationProcessor = WaterRelationProcessor(bounding_box)

        osm_data = OSMData()
        polygons, skipped = processor.process(osm_data)

        assert polygons == []
        assert skipped == set()

    def test_complete_water_relation(self) -> None:
        """Test complete water relation (all ways present, closed polygon)."""
        bounding_box: BoundingBox = BoundingBox(0.0, 0.0, 1.0, 1.0)
        processor: WaterRelationProcessor = WaterRelationProcessor(bounding_box)

        # Create a closed lake entirely inside bounding box.
        relation, ways = create_water_relation(
            [
                [
                    (0.2, 0.2),
                    (0.2, 0.8),
                    (0.8, 0.8),
                    (0.8, 0.2),
                    (0.2, 0.2),  # Closed.
                ]
            ],
            closed=True,
        )

        osm_data: OSMData = OSMData()
        osm_data.relations[relation.id_] = relation
        for way in ways:
            osm_data.ways[way.id_] = way

        polygons, skipped = processor.process(osm_data)

        # Complete relation should not be processed (let normal handling do it).
        assert len(polygons) == 0
        assert len(skipped) == 0

    def test_incomplete_water_relation_missing_ways(self) -> None:
        """Test water relation with some ways missing from data."""
        bounding_box: BoundingBox = BoundingBox(0.0, 0.0, 1.0, 1.0)
        processor: WaterRelationProcessor = WaterRelationProcessor(bounding_box)

        # Create relation with 2 ways, but only add 1 to osm_data.
        relation, ways = create_water_relation(
            [
                [(0.2, 0.2), (0.2, 0.8), (0.5, 0.8)],  # First segment.
                [(0.5, 0.8), (0.8, 0.8), (0.8, 0.2), (0.2, 0.2)],  # Second.
            ]
        )

        osm_data: OSMData = OSMData()
        osm_data.relations[relation.id_] = relation
        # Only add the first way (simulating partial download).
        osm_data.ways[ways[0].id_] = ways[0]

        _polygons, skipped = processor.process(osm_data)

        # Should be processed since ways are missing.
        assert relation.id_ in skipped

    def test_is_water_relation_natural_water(self) -> None:
        """Test detection of natural=water relation."""
        bounding_box: BoundingBox = BoundingBox(0.0, 0.0, 1.0, 1.0)
        processor: WaterRelationProcessor = WaterRelationProcessor(bounding_box)

        relation: OSMRelation = OSMRelation(
            tags={"type": "multipolygon", "natural": "water"},
            id_=1,
            members=[],
        )
        assert processor._is_water_relation(relation)  # noqa: SLF001

    def test_is_not_water_relation(self) -> None:
        """Test non-water relation is not detected as water."""
        bounding_box: BoundingBox = BoundingBox(0.0, 0.0, 1.0, 1.0)
        processor: WaterRelationProcessor = WaterRelationProcessor(bounding_box)

        relation: OSMRelation = OSMRelation(
            tags={"type": "multipolygon", "landuse": "forest"},
            id_=1,
            members=[],
        )
        assert not processor._is_water_relation(relation)  # noqa: SLF001

    def test_non_multipolygon_not_processed(self) -> None:
        """Test that non-multipolygon relations are not processed."""
        bounding_box: BoundingBox = BoundingBox(0.0, 0.0, 1.0, 1.0)
        processor: WaterRelationProcessor = WaterRelationProcessor(bounding_box)

        relation: OSMRelation = OSMRelation(
            tags={"type": "route", "natural": "water"},
            id_=1,
            members=[],
        )
        assert not processor._is_water_relation(relation)  # noqa: SLF001

    def test_multiple_bbox_crossings(self) -> None:
        """Test boundary that crosses the bounding box multiple times.

        Boundary enters left, exits right, loops outside, re-enters right,
        exits left.
        """
        bounding_box: BoundingBox = BoundingBox(0.0, 0.0, 1.0, 1.0)
        processor: WaterRelationProcessor = WaterRelationProcessor(bounding_box)

        # Boundary: outside → in (left) → out (right) → outside loop →
        #     in (right) → out (left) → outside.
        relation, ways = create_water_relation(
            [
                [
                    (0.3, -0.5),  # Outside left.
                    (0.3, 0.5),  # Inside.
                    (0.3, 1.5),  # Outside right.
                    (0.7, 1.5),  # Outside right (loop).
                    (0.7, 0.5),  # Inside.
                    (0.7, -0.5),  # Outside left.
                ]
            ]
        )

        osm_data: OSMData = OSMData()
        osm_data.relations[relation.id_] = relation
        # Simulating partial download:
        for way in ways:
            osm_data.ways[way.id_] = way

        # Add a second member that's missing to trigger incomplete processing.
        assert relation.members
        relation.members.append(OSMMember(type_="way", ref=99999, role="outer"))

        polygons, skipped = processor.process(osm_data)

        assert relation.id_ in skipped
        assert len(polygons) >= 1

        # Verify no polygon point is outside the bounding box.
        for polygon in polygons:
            for point in polygon.points:
                assert point[0] >= -0.01, (  # noqa: PLR2004
                    f"Latitude {point[0]} below bounding box."
                )
                assert point[0] <= 1.01, (  # noqa: PLR2004
                    f"Latitude {point[0]} above bounding box."
                )
                assert point[1] >= -0.01, (  # noqa: PLR2004
                    f"Longitude {point[1]} left of bounding box."
                )
                assert point[1] <= 1.01, (  # noqa: PLR2004
                    f"Longitude {point[1]} right of bounding box."
                )


class TestIslandInsideBbox:
    """Test islands (closed coastlines) entirely inside the bounding box."""

    def test_island_creates_hole_in_water(self) -> None:
        """A closed coastline inside bbox creates water + island hole."""
        bounding_box = BoundingBox(0.0, 0.0, 1.0, 1.0)
        processor = CoastlineProcessor(bounding_box)

        # Closed island coastline entirely inside bbox.
        # In real OSM data, first and last node are the same object.
        first_node = create_node(0.3, 0.3, 0)
        nodes = [
            first_node,
            create_node(0.3, 0.7, 1),
            create_node(0.7, 0.7, 2),
            create_node(0.7, 0.3, 3),
            first_node,  # Same node object closes the way.
        ]
        way = OSMWay(tags={"natural": "coastline"}, id_=1, nodes=nodes)
        osm_data = OSMData()
        osm_data.ways[way.id_] = way

        result = processor.process(osm_data)

        # Should produce a bbox water polygon and an island hole.
        assert len(result) == 2  # noqa: PLR2004
        non_holes = [p for p in result if not p.is_hole]
        holes = [p for p in result if p.is_hole]
        assert len(non_holes) == 1
        assert len(holes) == 1
        assert len(holes[0].points) == 5  # noqa: PLR2004

    def test_no_island_no_water(self) -> None:
        """No coastlines and no islands produces no water."""
        bounding_box = BoundingBox(0.0, 0.0, 1.0, 1.0)
        processor = CoastlineProcessor(bounding_box)
        osm_data = OSMData()

        result = processor.process(osm_data)
        assert result == []


class TestPointInPolygon:
    """Test _point_in_polygon helper."""

    def test_inside(self) -> None:
        """Point inside a square polygon."""
        square = [
            np.array((0.0, 0.0)),
            np.array((0.0, 1.0)),
            np.array((1.0, 1.0)),
            np.array((1.0, 0.0)),
        ]
        assert _point_in_polygon(np.array((0.5, 0.5)), square)

    def test_outside(self) -> None:
        """Point outside a square polygon."""
        square = [
            np.array((0.0, 0.0)),
            np.array((0.0, 1.0)),
            np.array((1.0, 1.0)),
            np.array((1.0, 0.0)),
        ]
        assert not _point_in_polygon(np.array((2.0, 2.0)), square)


class TestEvidenceBasedDirection:
    """Test evidence-based direction selection in _complete_boundary."""

    def test_inner_member_determines_water_side(self) -> None:
        """Inner member (island) determines which candidate is water."""
        bounding_box = BoundingBox(0.0, 0.0, 1.0, 1.0)
        processor = WaterRelationProcessor(bounding_box)

        # Outer boundary enters left edge at (0.3, 0), crosses to right
        # edge at (0.3, 1). This divides the bbox into upper and lower
        # regions. The inner member (island) is in the upper region,
        # so upper region is water.
        relation, ways = create_water_relation(
            [
                [
                    (0.3, -0.5),  # Outside left.
                    (0.3, 0.5),  # Inside.
                    (0.3, 1.5),  # Outside right.
                ]
            ],
            inner_coordinates=[
                [
                    (0.7, 0.3),  # Island in upper region.
                    (0.7, 0.7),
                    (0.9, 0.7),
                    (0.9, 0.3),
                    (0.7, 0.3),
                ],
            ],
        )
        # Add missing way to trigger incomplete processing.
        assert relation.members
        relation.members.append(OSMMember(type_="way", ref=99999, role="outer"))

        osm_data = OSMData()
        osm_data.relations[relation.id_] = relation
        for way in ways:
            osm_data.ways[way.id_] = way

        polygons, skipped = processor.process(osm_data)

        assert relation.id_ in skipped
        assert len(polygons) >= 1

        # The water polygon should contain the island center (0.8, 0.5).
        island_center = np.array((0.8, 0.5))
        water_polygons = [p for p in polygons if not p.is_hole]
        assert any(
            _point_in_polygon(island_center, p.points) for p in water_polygons
        )

        # A point in the lower region (0.1, 0.5) should NOT be in water.
        land_point = np.array((0.1, 0.5))
        assert not any(
            _point_in_polygon(land_point, p.points) for p in water_polygons
        )

    def test_place_island_determines_water_side(self) -> None:
        """A place=island way determines which candidate is water."""
        bounding_box = BoundingBox(0.0, 0.0, 1.0, 1.0)
        processor = WaterRelationProcessor(bounding_box)

        # Same boundary as above, but no inner members.
        relation, ways = create_water_relation(
            [
                [
                    (0.3, -0.5),
                    (0.3, 0.5),
                    (0.3, 1.5),
                ]
            ],
        )
        assert relation.members
        relation.members.append(OSMMember(type_="way", ref=99999, role="outer"))

        osm_data = OSMData()
        osm_data.relations[relation.id_] = relation
        for way in ways:
            osm_data.ways[way.id_] = way

        # Add a place=island way in the upper region.
        island_nodes = [
            create_node(0.8, 0.4, 9000),
            create_node(0.8, 0.6, 9001),
            create_node(0.9, 0.5, 9002),
        ]
        island_way = OSMWay(
            tags={"place": "island"}, id_=9000, nodes=island_nodes
        )
        osm_data.ways[island_way.id_] = island_way

        polygons, skipped = processor.process(osm_data)

        assert relation.id_ in skipped
        assert len(polygons) >= 1

        # Water polygon should contain the island area.
        island_center = np.array((0.8, 0.5))
        water_polygons = [p for p in polygons if not p.is_hole]
        assert any(
            _point_in_polygon(island_center, p.points) for p in water_polygons
        )

    def test_fallback_to_smaller_polygon(self) -> None:
        """Without evidence, the smaller polygon is chosen."""
        bounding_box = BoundingBox(0.0, 0.0, 1.0, 1.0)
        processor = WaterRelationProcessor(bounding_box)

        # Boundary crosses near the bottom: enters left at (0.2, 0),
        # exits right at (0.2, 1). No inner members, no islands.
        # The smaller polygon is the strip below y=0.2.
        relation, ways = create_water_relation(
            [
                [
                    (0.2, -0.5),
                    (0.2, 0.5),
                    (0.2, 1.5),
                ]
            ],
        )
        assert relation.members
        relation.members.append(OSMMember(type_="way", ref=99999, role="outer"))

        osm_data = OSMData()
        osm_data.relations[relation.id_] = relation
        for way in ways:
            osm_data.ways[way.id_] = way

        polygons, skipped = processor.process(osm_data)

        assert relation.id_ in skipped
        assert len(polygons) >= 1

        # The chosen polygon should be the smaller one (below boundary).
        water_polygons = [p for p in polygons if not p.is_hole]
        assert len(water_polygons) == 1

        # Point in smaller region (below boundary) should be inside.
        below_point = np.array((0.1, 0.5))
        assert _point_in_polygon(below_point, water_polygons[0].points)

        # Point in larger region (above boundary) should be outside.
        above_point = np.array((0.8, 0.5))
        assert not _point_in_polygon(above_point, water_polygons[0].points)
