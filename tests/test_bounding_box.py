"""Test bounding box."""

from map_machine.geometry.bounding_box import BoundingBox

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def test_round_zero_coordinates() -> None:
    """Test rounding for zero coordinates."""
    assert (
        BoundingBox(0, 0, 0, 0).round().get_format()
        == "-0.001,-0.001,0.001,0.001"
    )


def test_round_coordinates() -> None:
    """Test rounding coordinates."""
    box: BoundingBox = BoundingBox(
        10.067596435546875,
        46.094186149226466,
        10.0689697265625,
        46.09513848390771,
    ).round()

    assert box.get_format() == "10.067,46.093,10.070,46.096"


def test_bounding_box_parsing() -> None:
    """Test parsing bounding box from text."""
    assert BoundingBox.from_text("-0.1,-0.1,0.1,0.1") == BoundingBox(
        -0.1, -0.1, 0.1, 0.1
    )

    # Negative horizontal boundary.
    assert BoundingBox.from_text("0.1,-0.1,-0.1,0.1") is None

    # Negative vertical boundary.
    assert BoundingBox.from_text("-0.1,0.1,0.1,-0.1") is None

    # Wrong format.
    assert BoundingBox.from_text("wrong") is None
    assert BoundingBox.from_text("-O.1,-0.1,0.1,0.1") is None

    # Too big bounding box.
    assert BoundingBox.from_text("-20,-20,20,20") is None


def test_bounding_box_parsing_scientific() -> None:
    """Test parsing bounding box from text in scientific notation."""
    assert BoundingBox.from_text(
        "1.23e-03,4.56e-04,7.89e-02,1.01e-03"
    ) == BoundingBox(0.00123, 0.000456, 0.0789, 0.00101)
