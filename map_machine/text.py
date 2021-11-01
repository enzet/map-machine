"""
OSM address tag processing.
"""
from dataclasses import dataclass
from typing import Any

from colour import Color

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

DEFAULT_FONT_SIZE: float = 10.0
DEFAULT_COLOR: Color = Color("#444444")


@dataclass
class Label:
    """
    Text label.
    """

    text: str
    fill: Color = DEFAULT_COLOR
    size: float = DEFAULT_FONT_SIZE


def get_address(
    tags: dict[str, Any], draw_captions_mode: str, processed: set[str]
) -> list[str]:
    """
    Construct address text list from the tags.

    :param tags: OSM node, way or relation tags
    :param draw_captions_mode: captions mode ("all", "main", or "no")
    :param processed: set of processed tag keys
    """
    address: list[str] = []

    tag_names: list[str] = ["housenumber"]
    if draw_captions_mode == "address":
        tag_names += ["postcode", "country", "city", "street"]

    for tag_name in tag_names:
        key: str = f"addr:{tag_name}"
        if key in tags:
            address.append(tags[key])
            processed.add(key)

    return address


def format_voltage(value: str) -> str:
    """
    Format voltage value to more human-readable form.

    :param value: presumably string representation of integer, in Volts
    """
    try:
        int_value: int = int(value)
        if int_value % 1000 == 0:
            return f"{int(int_value / 1000)} kV"
        return f"{value} V"
    except ValueError:
        return value


def format_frequency(value: str) -> str:
    """Format frequency value to more human-readable form."""
    return f"{value} "


def get_text(tags: dict[str, Any], processed: set[str]) -> list[Label]:
    """Get text representation of writable tags."""
    texts: list[Label] = []
    values: list[str] = []

    if "voltage:primary" in tags:
        values.append(tags["voltage:primary"])
        processed.add("voltage:primary")

    if "voltage:secondary" in tags:
        values.append(tags["voltage:secondary"])
        processed.add("voltage:secondary")

    if "voltage" in tags:
        values = tags["voltage"].split(";")
        processed.add("voltage")

    if values:
        texts.append(Label(", ".join(map(format_voltage, values))))

    if "frequency" in tags:
        text: str = ", ".join(
            map(format_frequency, tags["frequency"].split(";"))
        )
        texts.append(Label(text))
        processed.add("frequency")

    return texts
