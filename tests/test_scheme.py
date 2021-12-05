"""
Test scheme parsing.
"""
from map_machine.scheme import Scheme


def test_verification() -> None:
    assert (
        Scheme({"node_icons": [{"tags": [{"tags": {"a": "b"}}]}]})
        .node_matchers[0]
        .verify()
        is True
    )
    assert (
        Scheme({"node_icons": [{"tags": [{"tags": {"a": 0}}]}]})
        .node_matchers[0]
        .verify()
        is False
    )
