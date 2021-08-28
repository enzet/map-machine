"""
Test zoom level specification parsing.
"""
from roentgen.tile import parse_zoom_level


def test_zoom_level_1() -> None:
    assert parse_zoom_level("18") == [18]


def test_zoom_level_list() -> None:
    assert parse_zoom_level("17,18") == [17, 18]
    assert parse_zoom_level("16,17,18") == [16, 17, 18]


def test_zoom_level_range() -> None:
    assert parse_zoom_level("16-18") == [16, 17, 18]
    assert parse_zoom_level("18-18") == [18]


def test_zoom_level_mixed() -> None:
    assert parse_zoom_level("15,16-18") == [15, 16, 17, 18]
    assert parse_zoom_level("15,16-18,20") == [15, 16, 17, 18, 20]
