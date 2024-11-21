"""Text processing for map element."""

from dataclasses import dataclass
from typing import Any, Optional

from colour import Color

from map_machine.map_configuration import LabelMode
from map_machine.osm.osm_reader import Tags
from map_machine.scheme import Scheme

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

DEFAULT_FONT_SIZE: float = 10.0


@dataclass
class Label:
    """Text label."""

    text: str
    fill: Color
    out_fill: Color
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


@dataclass
class TextConstructor:
    """Constructs map labels out of OpenStreetMap tags."""

    def __init__(self, scheme: Scheme) -> None:
        self.scheme: Scheme = scheme
        self.default_color: Color = self.scheme.get_color("text_color")
        self.main_color: Color = self.scheme.get_color("text_main_color")
        self.default_out_color: Color = self.scheme.get_color(
            "text_outline_color"
        )

    def label(self, text: str, size: float = DEFAULT_FONT_SIZE):
        return Label(
            text, self.default_color, self.default_out_color, size=size
        )

    def get_text(
        self, tags: dict[str, Any], processed: set[str]
    ) -> list[Label]:
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
            texts.append(self.label(", ".join(map(format_voltage, values))))

        if "frequency" in tags:
            text: str = ", ".join(
                map(format_frequency, tags["frequency"].split(";"))
            )
            texts.append(self.label(text))
            processed.add("frequency")

        return texts

    def construct_text(
        self,
        tags: Tags,
        processed: set[str],
        label_mode: LabelMode,
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
        elif "ref" in tags:
            name = tags["ref"]
            processed.add("ref")

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
            texts.append(Label(name, self.main_color, self.default_out_color))
        if alternative_name:
            texts.append(self.label(f"({alternative_name})"))
        if address:
            texts.append(self.label(", ".join(address)))

        if label_mode == LabelMode.MAIN:
            return texts

        texts += self.get_text(tags, processed)

        if "route_ref" in tags:
            texts.append(self.label(tags["route_ref"].replace(";", " ")))
            processed.add("route_ref")

        if "cladr:code" in tags:
            texts.append(self.label(tags["cladr:code"], size=7.0))
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
            texts.append(Label(link, Color("#000088"), self.default_out_color))
            processed.add("website")

        for key in ["phone"]:
            if key in tags:
                texts.append(
                    Label(tags[key], Color("#444444"), self.default_out_color)
                )
                processed.add(key)

        if "height" in tags:
            texts.append(self.label(f"↕ {tags['height']} m"))
            processed.add("height")

        for tag in tags:
            if self.scheme.is_writable(tag, tags[tag]) and tag not in processed:
                texts.append(
                    Label(
                        tags[tag],
                        self.default_color,
                        self.default_out_color,
                    )
                )
        return texts
