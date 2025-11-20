"""Test MapCSS generation."""

from map_machine.mapcss import MapCSSWriter
from map_machine.scheme import NodeMatcher
from tests import SCHEME

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def test_mapcss() -> None:
    """Test MapCSS generation."""
    writer: MapCSSWriter = MapCSSWriter(SCHEME, "icons")
    matcher: NodeMatcher = NodeMatcher(
        {"tags": {"natural": "tree"}, "shapes": ["tree"]}, {}
    )
    selector = writer.add_selector("node", matcher)
    assert (
        selector
        == """\
node[natural="tree"] {
    icon-image: "icons/tree.svg";
}
"""
    )
