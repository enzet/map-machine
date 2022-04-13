"""
Test scheme parsing.
"""
from typing import Any

from map_machine.scheme import Scheme


def test_verification() -> None:
    """Test verification process of tags in scheme."""

    tags: dict[str, Any] = {
        "colors": {"default": "#444444"},
        "node_icons": [{"tags": [{"tags": {"a": "b"}}]}],
    }
    assert Scheme(tags).node_matchers[0].verify() is True

    # Tag value should be string, not integer.

    tags: dict[str, Any] = {
        "colors": {"default": "#444444"},
        "node_icons": [{"tags": [{"tags": {"a": 0}}]}],
    }
    assert Scheme(tags).node_matchers[0].verify() is False
