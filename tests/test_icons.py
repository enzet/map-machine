"""
Test icon generation for nodes.
"""
import pytest
from colour import Color

from map_machine.grid import IconCollection
from map_machine.icon import IconSet
from tests import SCHEME, SHAPE_EXTRACTOR, workspace

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


@pytest.fixture
def init_collection() -> IconCollection:
    """Create collection of all possible icon sets."""
    return IconCollection.from_scheme(SCHEME, SHAPE_EXTRACTOR)


def test_grid(init_collection: IconCollection) -> None:
    """Test grid drawing."""
    init_collection.draw_grid(workspace.output_path / "grid.svg")


def test_icons_by_id(init_collection: IconCollection) -> None:
    """Test individual icons drawing."""
    init_collection.draw_icons(workspace.get_icons_by_id_path())


def test_icons_by_name(init_collection: IconCollection) -> None:
    """Test drawing individual icons that have names."""
    init_collection.draw_icons(workspace.get_icons_by_name_path(), by_name=True)


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
    icon = get_icon({"aaa": "bbb"})
    assert icon.main_icon.is_default()


def test_icon() -> None:
    """
    Tags that should be visualized with single main icon and without extra
    icons.
    """
    icon: IconSet = get_icon({"natural": "tree"})
    assert not icon.main_icon.is_default()
    assert len(icon.main_icon.shape_specifications) == 1
    assert icon.main_icon.shape_specifications[0].shape.id_ == "tree"
    assert icon.main_icon.shape_specifications[0].color == Color("#98AC64")
    assert not icon.extra_icons


def test_icon_1_extra() -> None:
    """
    Tags that should be visualized with single main icon and single extra icon.
    """
    icon = get_icon({"barrier": "gate", "access": "private"})
    assert not icon.main_icon.is_default()
    assert len(icon.extra_icons) == 1


def test_icon_2_extra() -> None:
    """
    Tags that should be visualized with single main icon and two extra icons.
    """
    icon = get_icon({"barrier": "gate", "access": "private", "bicycle": "yes"})
    assert not icon.main_icon.is_default()
    assert len(icon.extra_icons) == 2


def test_no_icon_1_extra() -> None:
    """
    Tags that should be visualized with default main icon and single extra icon.
    """
    icon = get_icon({"access": "private"})
    assert icon.main_icon.is_default()
    assert len(icon.extra_icons) == 1


def test_no_icon_2_extra() -> None:
    """
    Tags that should be visualized with default main icon and two extra icons.
    """
    icon = get_icon({"access": "private", "bicycle": "yes"})
    assert icon.main_icon.is_default()
    assert len(icon.extra_icons) == 2
