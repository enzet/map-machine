"""
Test icon generation for nodes.

Author: Sergey Vartanov (me@enzet.ru).
"""
from os import makedirs
from pathlib import Path
from typing import Dict

from roentgen.grid import draw_all_icons
from roentgen.icon import ShapeExtractor
from roentgen.scheme import Scheme

SCHEME: Scheme = Scheme("scheme/default.yml")
ICON_EXTRACTOR: ShapeExtractor = ShapeExtractor(
    "icons/icons.svg", Path("icons/config.json")
)


def test_icons() -> None:
    """ Test grid drawing. """
    makedirs("icon_set", exist_ok=True)
    draw_all_icons("temp.svg", "icon_set")


def get_icon(tags: Dict[str, str]):
    icon, _ = SCHEME.get_icon(ICON_EXTRACTOR, tags)
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
    icon = get_icon({"natural": "tree"})
    assert not icon.main_icon.is_default()
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
