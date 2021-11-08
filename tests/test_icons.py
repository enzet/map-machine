"""
Test icon generation for nodes.
"""
from typing import Optional

from colour import Color

from map_machine.pictogram.icon import IconSet, ShapeSpecification, Icon
from map_machine.pictogram.icon_collection import IconCollection
from tests import SCHEME, SHAPE_EXTRACTOR, workspace

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


COLLECTION: IconCollection = IconCollection.from_scheme(SCHEME, SHAPE_EXTRACTOR)


def test_grid() -> None:
    """Test grid drawing."""
    COLLECTION.draw_grid(workspace.output_path / "grid.svg")


def test_icons_by_id() -> None:
    """Test individual icons drawing."""
    COLLECTION.draw_icons(workspace.get_icons_by_id_path())


def test_icons_by_name() -> None:
    """Test drawing individual icons that have names."""
    COLLECTION.draw_icons(workspace.get_icons_by_name_path(), by_name=True)


def get_icon(tags: dict[str, str]) -> IconSet:
    """Construct icon from tags."""
    processed: set[str] = set()
    icon, _ = SCHEME.get_icon(SHAPE_EXTRACTOR, tags, processed)
    return icon


def test_no_icons() -> None:
    """
    Tags that has no description in scheme and should be visualized with default
    shape.
    """
    icon: IconSet = get_icon({"aaa": "bbb"})
    assert icon.main_icon.is_default()


def check_icon_set(
    icon: IconSet,
    main_specification: list[tuple[str, Optional[str]]],
    extra_specifications: list[list[tuple[str, Optional[str]]]],
) -> None:
    """Check icon set using simple specification."""
    if not main_specification:
        assert icon.main_icon.is_default()
    else:
        assert not icon.main_icon.is_default()
        assert len(main_specification) == len(
            icon.main_icon.shape_specifications
        )
        for index, shape in enumerate(main_specification):
            shape_specification: ShapeSpecification = (
                icon.main_icon.shape_specifications[index]
            )
            assert shape_specification.shape.id_ == shape[0]
            assert shape_specification.color == Color(shape[1])

    assert len(extra_specifications) == len(icon.extra_icons)
    for i, extra_specification in enumerate(extra_specifications):
        extra_icon: Icon = icon.extra_icons[i]
        assert len(extra_specification) == len(extra_icon.shape_specifications)
        for j, shape in enumerate(extra_specification):
            assert extra_icon.shape_specifications[j].shape.id_ == shape[0]
            assert extra_icon.shape_specifications[j].color == Color(shape[1])


def test_icon() -> None:
    """
    Tags that should be visualized with single main icon and without extra
    icons.
    """
    icon: IconSet = get_icon({"natural": "tree"})
    check_icon_set(icon, [("tree", "#98AC64")], [])


def test_icon_1_extra() -> None:
    """
    Tags that should be visualized with single main icon and single extra icon.
    """
    icon: IconSet = get_icon({"barrier": "gate", "access": "private"})
    check_icon_set(
        icon, [("gate", "#444444")], [[("lock_with_keyhole", "#888888")]]
    )


def test_icon_2_extra() -> None:
    """
    Tags that should be visualized with single main icon and two extra icons.
    """
    icon: IconSet = get_icon(
        {"barrier": "gate", "access": "private", "bicycle": "yes"}
    )
    check_icon_set(
        icon,
        [("gate", "#444444")],
        [
            [("bicycle", "#888888")],
            [("lock_with_keyhole", "#888888")],
        ],
    )


def test_no_icon_1_extra() -> None:
    """
    Tags that should be visualized with default main icon and single extra icon.
    """
    icon: IconSet = get_icon({"access": "private"})
    check_icon_set(icon, [], [[("lock_with_keyhole", "#888888")]])


def test_no_icon_2_extra() -> None:
    """
    Tags that should be visualized with default main icon and two extra icons.
    """
    icon: IconSet = get_icon({"access": "private", "bicycle": "yes"})
    check_icon_set(
        icon,
        [],
        [
            [("bicycle", "#888888")],
            [("lock_with_keyhole", "#888888")],
        ],
    )


def test_icon_regex() -> None:
    """
    Tags that should be visualized with default main icon and single extra icon.
    """
    icon: IconSet = get_icon({"traffic_sign": "maxspeed", "maxspeed": "42"})
    check_icon_set(
        icon,
        [
            ("circle_11", "#444444"),
            ("digit_4", "#FFFFFF"),
            ("digit_2", "#FFFFFF"),
        ],
        [],
    )
