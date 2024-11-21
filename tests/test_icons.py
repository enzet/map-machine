"""
Test icon generation for nodes.

Tests check that for the given node described by tags, Map Machine generates
expected icons with expected colors.
"""

from pathlib import Path
from typing import Optional

from colour import Color

from map_machine.map_configuration import MapConfiguration
from map_machine.osm.osm_reader import Tags
from map_machine.pictogram.icon import IconSet, ShapeSpecification, Icon
from map_machine.pictogram.icon_collection import IconCollection
from tests import SCHEME, SHAPE_EXTRACTOR, workspace

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


CONFIGURATION: MapConfiguration = MapConfiguration(SCHEME)
COLLECTION: IconCollection = IconCollection.from_scheme(SCHEME, SHAPE_EXTRACTOR)
DEFAULT_COLOR: Color = SCHEME.get_default_color()
EXTRA_COLOR: Color = SCHEME.get_extra_color()
WHITE: Color = Color("white")


def test_grid() -> None:
    """Test grid drawing."""
    COLLECTION.draw_grid(workspace.output_path / "grid.svg")


def test_icons_by_id() -> None:
    """Test individual icons drawing."""
    path: Path = workspace.get_icons_by_id_path()
    COLLECTION.draw_icons(path, workspace.ICONS_LICENSE_PATH)
    assert (path / "tree.svg").is_file()
    assert (path / "LICENSE").is_file()


def test_icons_by_name() -> None:
    """Test drawing individual icons that have names."""
    path: Path = workspace.get_icons_by_name_path()
    COLLECTION.draw_icons(path, workspace.ICONS_LICENSE_PATH, by_name=True)
    assert (path / "Röntgen tree.svg").is_file()
    assert (path / "LICENSE").is_file()


def get_icon(tags: Tags) -> IconSet:
    """Construct icon from tags."""
    processed: set[str] = set()
    icon, _ = CONFIGURATION.get_icon(SHAPE_EXTRACTOR, tags, processed)
    return icon


def test_no_icons() -> None:
    """
    Test icon creation for tags not described in the scheme.

    Tags that has no description in the scheme and should be visualized with
    default shape.
    """
    icon: IconSet = get_icon({"aaa": "bbb"})
    assert icon.main_icon.is_default()
    assert icon.main_icon.shape_specifications[0].color == DEFAULT_COLOR


def test_no_icons_but_color() -> None:
    """
    Test icon creation for tags not described in the scheme and `colour` tag.

    Tags that has no description in scheme, but have `colour` tag and should be
    visualized with default shape with the given color.
    """
    icon: IconSet = get_icon({"aaa": "bbb", "colour": "#424242"})
    assert icon.main_icon.is_default()
    assert icon.main_icon.shape_specifications[0].color == Color("#424242")


def check_icon_set(
    tags: Tags,
    main_specification: list[tuple[str, Optional[Color]]],
    extra_specifications: list[list[tuple[str, Optional[Color]]]] = None,
) -> None:
    """Check icon set using simple specification."""
    icon: IconSet = get_icon(tags)

    if extra_specifications is None:
        extra_specifications = []

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
    check_icon_set({"natural": "tree"}, [("tree", Color("#98AC64"))])


def test_icon_1_extra() -> None:
    """
    Tags that should be visualized with single main icon and single extra icon.
    """
    check_icon_set(
        {"barrier": "gate", "access": "private"},
        [("gate", DEFAULT_COLOR)],
        [[("lock_with_keyhole", EXTRA_COLOR)]],
    )


def test_icon_2_extra() -> None:
    """
    Tags that should be visualized with single main icon and two extra icons.
    """
    check_icon_set(
        {"barrier": "gate", "access": "private", "bicycle": "yes"},
        [("gate", DEFAULT_COLOR)],
        [
            [("bicycle", EXTRA_COLOR)],
            [("lock_with_keyhole", EXTRA_COLOR)],
        ],
    )


def test_no_icon_1_extra() -> None:
    """
    Tags that should be visualized without main icon and with single extra icon.
    """
    check_icon_set(
        {"access": "private"}, [], [[("lock_with_keyhole", EXTRA_COLOR)]]
    )


def test_no_icon_2_extra() -> None:
    """
    Tags that should be visualized with default main icon and two extra icons.
    """
    check_icon_set(
        {"access": "private", "bicycle": "yes"},
        [],
        [[("bicycle", EXTRA_COLOR)], [("lock_with_keyhole", EXTRA_COLOR)]],
    )


def test_icon_regex() -> None:
    """Check that simple regular expressions work properly."""
    check_icon_set(
        {"traffic_sign": "maxspeed", "maxspeed": "42"},
        [("circle_11", DEFAULT_COLOR), ("digit_4", WHITE), ("digit_2", WHITE)],
    )


def test_vending_machine() -> None:
    """
    Check that specific vending machines aren't rendered with generic icon.

    See https://github.com/enzet/map-machine/issues/132
    """
    check_icon_set(
        {"amenity": "vending_machine"},
        [("vending_machine", DEFAULT_COLOR)],
    )
    check_icon_set(
        {"amenity": "vending_machine", "vending": "drinks"},
        [("vending_bottle", DEFAULT_COLOR)],
    )
    check_icon_set(
        {"vending": "drinks"},
        [("vending_bottle", DEFAULT_COLOR)],
    )


def test_diving_tower() -> None:
    """
    Check that diving towers are rendered as diving towers, not just
    freestanding towers.

    See https://github.com/enzet/map-machine/issues/138
    """
    check_icon_set(
        {
            "man_made": "tower",
            "tower:type": "diving",
            "tower:construction": "freestanding",
            "tower:platforms": "4",
        },
        [("diving_4_platforms", DEFAULT_COLOR)],
    )
