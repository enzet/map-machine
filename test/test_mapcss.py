"""
Test MapCSS generation.
"""
from roentgen.mapcss import MapCSSWriter
from roentgen.scheme import NodeMatcher
from test import SCHEME

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def test_mapcss() -> None:
    """
    Test MapCSS generation.
    """
    writer: MapCSSWriter = MapCSSWriter(SCHEME, "icons")
    matcher: NodeMatcher = NodeMatcher(
        {"tags": {"natural": "tree"}, "shapes": ["tree"]}
    )
    selector = writer.add_selector("node", matcher)
    assert (
        selector
        == """node[natural="tree"] {
    icon-image: "icons/tree.svg";
}
"""
    )
