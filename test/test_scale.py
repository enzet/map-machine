"""
Test scale specification parsing.
"""
from roentgen.tile import parse_scale


def test_scale_1() -> None:
    assert parse_scale("18") == [18]


def test_scale_list() -> None:
    assert parse_scale("17,18") == [17, 18]
    assert parse_scale("16,17,18") == [16, 17, 18]


def test_scale_range() -> None:
    assert parse_scale("16-18") == [16, 17, 18]
    assert parse_scale("18-18") == [18]


def test_scale_mixed() -> None:
    assert parse_scale("15,16-18") == [15, 16, 17, 18]
    assert parse_scale("15,16-18,20") == [15, 16, 17, 18, 20]
