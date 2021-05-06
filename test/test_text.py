"""
Author: Sergey Vartanov (me@enzet.ru).
"""
from roentgen.scheme import Scheme


def get_text(tags):
    scheme = Scheme("data/tags.yml")
    return scheme.construct_text(tags, True)


def test_1_label() -> None:
    labels = get_text({"name": "Name"})
    assert len(labels) == 1
    assert labels[0].text == "Name"


def test_1_label_unknown_tags() -> None:
    labels = get_text({"name": "Name", "aaa": "bbb"})
    assert len(labels) == 1
    assert labels[0].text == "Name"


def test_2_labels() -> None:
    labels = get_text({"name": "Name", "ref": "5"})
    assert len(labels) == 2
    assert labels[0].text == "Name"
    assert labels[1].text == "5"
