"""Test boundary box."""

from map_machine.geometry.boundary_box import BoundaryBox

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def test_round_zero_coordinates() -> None:
    """Test rounding for zero coordinates."""
    assert (
        BoundaryBox(0, 0, 0, 0).round().get_format()
        == "-0.001,-0.001,0.001,0.001"
    )


def test_round_coordinates() -> None:
    """Test rounding coordinates."""
    box: BoundaryBox = BoundaryBox(
        10.067596435546875,
        46.094186149226466,
        10.0689697265625,
        46.09513848390771,
    ).round()

    assert box.get_format() == "10.067,46.093,10.070,46.096"


def test_boundary_box_parsing() -> None:
    """Test parsing boundary box from text."""
    assert BoundaryBox.from_text("-0.1,-0.1,0.1,0.1") == BoundaryBox(
        -0.1, -0.1, 0.1, 0.1
    )

    # Negative horizontal boundary.
    assert BoundaryBox.from_text("0.1,-0.1,-0.1,0.1") is None

    # Negative vertical boundary.
    assert BoundaryBox.from_text("-0.1,0.1,0.1,-0.1") is None

    # Wrong format.
    assert BoundaryBox.from_text("wrong") is None
    assert BoundaryBox.from_text("-O.1,-0.1,0.1,0.1") is None

    # Too big boundary box.
    assert BoundaryBox.from_text("-20,-20,20,20") is None
