"""
Test boundary box.
"""
from roentgen.ui import BoundaryBox

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def test_round_zero_coordinates() -> None:
    assert (
        BoundaryBox(0, 0, 0, 0).round().get_format()
        == "-0.001,-0.001,0.001,0.001"
    )


def test_round_coordinates() -> None:
    box: BoundaryBox = BoundaryBox(
        10.067596435546875,
        46.094186149226466,
        10.0689697265625,
        46.09513848390771,
    ).round()

    assert box.get_format() == "10.067,46.093,10.070,46.096"
