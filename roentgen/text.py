"""
OSM address tag processing.
"""
from dataclasses import dataclass
from typing import Any, Dict, List

from colour import Color

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

DEFAULT_COLOR: Color = Color("#444444")


@dataclass
class Label:
    """
    Text label.
    """
    text: str
    fill: Color = DEFAULT_COLOR
    size: float = 10.0


def get_address(tags: Dict[str, Any], draw_captions_mode: str) -> List[str]:
    """
    Construct address text list from the tags.

    :param tags: OSM node, way or relation tags
    :param draw_captions_mode: captions mode ("all", "main", or "no")
    """
    address: List[str] = []

    if draw_captions_mode == "address":
        if "addr:postcode" in tags:
            address.append(tags["addr:postcode"])
            tags.pop("addr:postcode", None)
        if "addr:country" in tags:
            address.append(tags["addr:country"])
            tags.pop("addr:country", None)
        if "addr:city" in tags:
            address.append(tags["addr:city"])
            tags.pop("addr:city", None)
        if "addr:street" in tags:
            street = tags["addr:street"]
            if street.startswith("улица "):
                street = "ул. " + street[len("улица "):]
            address.append(street)
            tags.pop("addr:street", None)

    if "addr:housenumber" in tags:
        address.append(tags["addr:housenumber"])
        tags.pop("addr:housenumber", None)

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
    """
    Format frequency value to more human-readable form.
    """
    try:
        return f"{value} Hz"
    except ValueError:
        return value


def get_text(tags: Dict[str, Any]) -> List[Label]:
    """
    Get text representation of writable tags.
    """
    texts: List[Label] = []

    values: List[str] = []
    if "voltage:primary" in tags:
        values.append(tags["voltage:primary"])
    if "voltage:secondary" in tags:
        values.append(tags["voltage:secondary"])
    if "voltage" in tags:
        values = tags["voltage"].split(";")
    if values:
        texts.append(Label(", ".join(map(format_voltage, values))))

    if "frequency" in tags:
        texts.append(Label(", ".join(map(
            format_frequency, tags["frequency"].split(";")
        ))))

    return texts
