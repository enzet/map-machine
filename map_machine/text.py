"""
OSM address tag processing.
"""
from dataclasses import dataclass
from typing import Any, Optional

from colour import Color

from map_machine.map_configuration import LabelMode
from map_machine.osm.osm_reader import Tags

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

DEFAULT_FONT_SIZE: float = 10.0
DEFAULT_COLOR: Color = Color("#444444")


@dataclass
class Label:
    """Text label."""

    text: str
    fill: Color = DEFAULT_COLOR
    size: float = DEFAULT_FONT_SIZE


def get_address(
    tags: dict[str, Any], processed: set[str], label_mode: LabelMode
) -> list[str]:
    """
    Construct address text list from the tags.

    :param tags: OSM node, way or relation tags
    :param processed: set of processed tag keys
    :param label_mode: captions mode
    """
    address: list[str] = []

    tag_names: list[str] = ["housenumber"]
    if label_mode == LabelMode.ADDRESS:
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


def construct_text(
    tags: Tags, processed: set[str], label_mode: LabelMode
) -> list[Label]:
    """Construct list of labels from OSM tags."""

    texts: list[Label] = []

    name: Optional[str] = None
    alternative_name: Optional[str] = None

    if "name" in tags:
        name = tags["name"]
        processed.add("name")
    elif "name:en" in tags:
        if not name:
            name = tags["name:en"]
            processed.add("name:en")
        processed.add("name:en")
    if "alt_name" in tags:
        if alternative_name:
            alternative_name += ", "
        else:
            alternative_name = ""
        alternative_name += tags["alt_name"]
        processed.add("alt_name")
    if "old_name" in tags:
        if alternative_name:
            alternative_name += ", "
        else:
            alternative_name = ""
        alternative_name += "ex " + tags["old_name"]

    address: list[str] = get_address(tags, processed, label_mode)

    if name:
        texts.append(Label(name, Color("black")))
    if alternative_name:
        texts.append(Label(f"({alternative_name})"))
    if address:
        texts.append(Label(", ".join(address)))

    if label_mode == LabelMode.MAIN:
        return texts

    texts += get_text(tags, processed)

    if "route_ref" in tags:
        texts.append(Label(tags["route_ref"].replace(";", " ")))
        processed.add("route_ref")

    if "cladr:code" in tags:
        texts.append(Label(tags["cladr:code"], size=7.0))
        processed.add("cladr:code")

    if "website" in tags:
        link = tags["website"]
        if link[:7] == "http://":
            link = link[7:]
        if link[:8] == "https://":
            link = link[8:]
        if link[:4] == "www.":
            link = link[4:]
        if link[-1] == "/":
            link = link[:-1]
        link = link[:25] + ("..." if len(tags["website"]) > 25 else "")
        texts.append(Label(link, Color("#000088")))
        processed.add("website")

    for key in ["phone"]:
        if key in tags:
            texts.append(Label(tags[key], Color("#444444")))
            processed.add(key)

    if "height" in tags:
        texts.append(Label(f"↕ {tags['height']} m"))
        processed.add("height")

    return texts
