"""Automate OpenStreetMap wiki editing."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from map_machine.map_configuration import MapConfiguration
from map_machine.scheme import Scheme
from map_machine.workspace import Workspace

if TYPE_CHECKING:
    from roentgen.icon import IconSpecification

    from map_machine.doc.doc_collections import Collection

WORKSPACE: Workspace = Workspace(Path("temp"))

SCHEME: Scheme = Scheme.from_file(WORKSPACE.DEFAULT_SCHEME_PATH)

HEADER_PATTERN: re.Pattern = re.compile("==?=?.*==?=?")
HEADER_2_PATTERN: re.Pattern = re.compile("== .* ==")
HEADER_PATTERNS: list[re.Pattern] = [
    re.compile("==\\s*Example.*=="),
    re.compile("==\\s*See also\\s*=="),
]
RENDERING_HEADER_PATTERN: re.Pattern = re.compile("==\\s*Rendering.*==")
ROENTGEN_HEADER_PATTERN: re.Pattern = re.compile("===.*Röntgen.*===")


class WikiTable:
    """Trivial wiki table constructor.

    Creates table with icon combinations.
    """

    def __init__(self, collection: Collection, page_name: str) -> None:
        self.collection: Collection = collection
        self.page_name: str = page_name

    def generate_wiki_table(self) -> tuple[str, list[IconSpecification]]:
        """Generate Röntgen icon table for the OpenStreetMap wiki page."""
        icons: list[IconSpecification] = []
        text: str = '{| class="wikitable"\n'

        if self.collection.column_key is not None:
            text += f"! {{{{Key|{self.collection.column_key}}}}}"
        else:
            text += "! Tag || Icon"

        if self.collection.row_tags:
            text += "\n"
            for current_tags in self.collection.row_tags:
                text += "|-\n"
                text += "| "
                if current_tags:
                    for key, value in current_tags.items():
                        if value == "*":
                            text += f"{{{{Key|{key}}}}}<br />"
                        else:
                            text += f"{{{{Tag|{key}|{value}}}}}<br />"
                    text = text[:-6]
                text += "\n"
                icon, _ = MapConfiguration(
                    SCHEME, ignore_level_matching=True
                ).get_icon(current_tags | self.collection.tags, set())
                if icon:
                    icons.append(icon.main_icon)
                    text += (
                        "| [[Image:Röntgen "
                        f"{icon.main_icon.get_name()}.svg|32px]]\n"
                    )
            text += "|}\n"
            return text, icons

        if not self.collection.column_values:
            self.collection.column_values = [""]
        else:
            make_vertical: bool = False
            for column_value in self.collection.column_values:
                if column_value and len(column_value) > 2:  # noqa: PLR2004
                    make_vertical = True
            for column_value in self.collection.column_values:
                text += " ||"
                if column_value:
                    tag: str = (
                        f"{{{{TagValue|"
                        f"{self.collection.column_key}|{column_value}}}}}"
                    )
                    text += " " + (
                        f"{{{{vert header|{tag}}}}}" if make_vertical else tag
                    )
        text += "\n"

        for row_value in self.collection.row_values:
            text += "|-\n"
            if row_value:
                text += f"| {{{{Tag|{self.collection.row_key}|{row_value}}}}}\n"
            else:
                text += "|\n"
            for column_value in self.collection.column_values:
                current_tags = dict(self.collection.tags) | {
                    self.collection.row_key: row_value
                }
                if column_value and self.collection.column_key:
                    current_tags |= {self.collection.column_key: column_value}
                icon, _ = MapConfiguration(SCHEME).get_icon(current_tags, set())
                if icon:
                    text += (
                        "| [[Image:Röntgen "
                        f"{icon.main_icon.get_name()}.svg|32px]]\n"
                    )
                    icons.append(icon.main_icon)

        text += "|}\n"

        return text, icons


def generate_new_text(
    old_text: str,
    table: WikiTable,
) -> tuple[str | None, list[IconSpecification]]:
    """Generate Röntgen icon table for the OpenStreetMap wiki page.

    :param old_text: previous wiki page text
    :param table: wiki table generator
    :return: new wiki page text
    """
    wiki_text: str
    icons: list[IconSpecification] = []

    if table.collection.row_key or table.collection.row_tags:
        wiki_text, icons = table.generate_wiki_table()
    else:
        processed: set[str] = set()
        icon, _ = MapConfiguration(SCHEME).get_icon(
            table.collection.tags, processed
        )
        if icon and not icon.main_icon.is_default():
            wiki_text = (
                f"[[Image:Röntgen {icon.main_icon.get_name()}.svg|32px]]\n"
            )
            icons.append(icon.main_icon)
        elif icon and icon.extra_icons:
            wiki_text = (
                f"Röntgen icon set has additional icon for the tag: "
                f"[[Image:Röntgen {icon.extra_icons[0].get_name()}.svg|32px]]."
                f"\n"
            )
            icons.append(icon.extra_icons[0])
        else:
            wiki_text = ""

    lines: list[str] = old_text.split("\n")

    # If rendering section already exists.

    start: int | None = None
    end: int = -1

    for index, line in enumerate(lines):
        if HEADER_2_PATTERN.match(line) and start is not None:
            end = index
            break
        if RENDERING_HEADER_PATTERN.match(line):
            start = index

    if start is not None:
        return (
            "\n".join(lines[: start + 2])
            + "\n=== [[Röntgen]] icons in [[Map Machine]] ===\n"
            + f"\n{wiki_text}\n"
            + "\n".join(lines[end:])
        ), icons

    # If Röntgen rendering section already exists.

    start = None
    end = -1

    for index, line in enumerate(lines):
        if HEADER_PATTERN.match(line) and start is not None:
            end = index
            break
        if ROENTGEN_HEADER_PATTERN.match(line):
            start = index

    if start is not None:
        return (
            "\n".join(lines[: start + 2])
            + f"\n{wiki_text}\n"
            + "\n".join(lines[end:])
        ), icons

    # Otherwise.

    headers: list[int | None] = [None, None]

    for index, line in enumerate(lines):
        for i, pattern in enumerate(HEADER_PATTERNS):
            if pattern.match(line):
                headers[i] = index

    filtered = [x for x in headers if x is not None]
    header: int

    if filtered:
        header = filtered[0]
    else:
        lines += [""]
        header = len(lines)

    return (
        "\n".join(lines[:header])
        + "\n== Rendering ==\n\n=== [[Röntgen]] icons in [[Map Machine]] "
        "===\n\n" + wiki_text + "\n" + "\n".join(lines[header:])
    ), icons
