"""
Test label generation for nodes.
"""
from typing import List

from roentgen.text import Label
from test import SCHEME

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def construct_labels(tags) -> List[Label]:
    """
    Construct labels from OSM node tags.
    """
    return SCHEME.construct_text(tags, "all")


def test_1_label() -> None:
    """
    Test tags that should be converted into single label.
    """
    labels = construct_labels({"name": "Name"})
    assert len(labels) == 1
    assert labels[0].text == "Name"


def test_1_label_unknown_tags() -> None:
    """
    Test tags with some unknown tags that should be converted into single label.
    """
    labels = construct_labels({"name": "Name", "aaa": "bbb"})
    assert len(labels) == 1
    assert labels[0].text == "Name"


def test_2_labels() -> None:
    """
    Test tags that should be converted into two labels.
    """
    labels = construct_labels({"name": "Name", "ref": "5"})
    assert len(labels) == 2
    assert labels[0].text == "Name"
    assert labels[1].text == "5"
