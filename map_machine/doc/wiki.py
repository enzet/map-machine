"""
Automate OpenStreetMap wiki editing.
"""
import re
from pathlib import Path
from typing import Optional

from map_machine.doc.collections import Collection
from map_machine.map_configuration import MapConfiguration
from map_machine.osm.osm_reader import Tags
from map_machine.pictogram.icon import Icon, ShapeExtractor
from map_machine.scheme import Scheme
from map_machine.workspace import Workspace

WORKSPACE: Workspace = Workspace(Path("temp"))

SCHEME: Scheme = Scheme(WORKSPACE.DEFAULT_SCHEME_PATH)
EXTRACTOR: ShapeExtractor = ShapeExtractor(
    WORKSPACE.ICONS_PATH, WORKSPACE.ICONS_CONFIG_PATH
)

HEADER_PATTERN: re.Pattern = re.compile("==?=?.*==?=?")
SEE_ALSO_HEADER_PATTERN: re.Pattern = re.compile("==\\s*See also\\s*==")
EXAMPLE_HEADER_PATTERN: re.Pattern = re.compile("==\\s*Example.*==")
RENDERING_HEADER_PATTERN: re.Pattern = re.compile(
    "===\\s*\\[\\[Röntgen]] icons\\s*==="
)


class WikiTable:
    """SVG table with icon combinations."""

    def __init__(self, collection: Collection, page_name: str):
        self.collection: Collection = collection
        self.page_name: str = page_name

    def generate_wiki_table(self) -> tuple[str, list[Icon]]:
        """
        Generate Röntgen icon table for the OpenStreetMap wiki page.
        """
        icons: list[Icon] = []
        text: str = '{| class="wikitable"\n'

        if self.collection.column_key is not None:
            text += f"! {{{{Key|{self.collection.column_key}}}}}"
        else:
            text += "! Tag || Icon"

        if not self.collection.column_values:
            self.collection.column_values = [""]
        else:
            for column_value in self.collection.column_values:
                text += " ||"
                if column_value:
                    text += (
                        f" {{{{vert header|{{{{TagValue|"
                        f"{self.collection.column_key}|{column_value}}}}}}}}}"
                    )
        text += "\n"

        processed: set[str] = set()

        for row_value in self.collection.row_values:
            text += "|-\n"
            if row_value:
                text += f"| {{{{Tag|{self.collection.row_key}|{row_value}}}}}\n"
            else:
                text += "|\n"
            for column_value in self.collection.column_values:
                current_tags: Tags = dict(self.collection.tags) | {
                    self.collection.row_key: row_value
                }
                if column_value:
                    current_tags |= {self.collection.column_key: column_value}
                icon, _ = SCHEME.get_icon(
                    EXTRACTOR, current_tags, processed, MapConfiguration()
                )
                if not icon:
                    print("Icon was not constructed.")
                text += (
                    "| "
                    f"[[Image:Röntgen {icon.main_icon.get_name()}.svg|32px]]\n"
                )
                icons.append(icon.main_icon)

        text += "|}\n"

        return text, icons


def generate_new_text(
    old_text: str,
    table: WikiTable,
) -> tuple[Optional[str], list[Icon]]:
    """
    Generate Röntgen icon table for the OpenStreetMap wiki page.

    :param old_text: previous wiki page text
    :param table: wiki table generator
    :return: new wiki page text
    """
    wiki_text: str
    icons = []

    if table.collection.row_key:
        wiki_text, icons = table.generate_wiki_table()
    else:
        processed = set()
        icon, _ = SCHEME.get_icon(
            EXTRACTOR, table.collection.tags, processed, MapConfiguration()
        )
        if not icon.main_icon.is_default():
            wiki_text = (
                f"[[Image:Röntgen {icon.main_icon.get_name()}.svg|32px]]\n"
            )
            icons.append(icon.main_icon)
        elif icon.extra_icons:
            wiki_text = (
                f"Röntgen icon set has additional icon for the tag: "
                f"[[Image:Röntgen {icon.extra_icons[0].get_name()}.svg|32px]]."
                f"\n"
            )
            icons.append(icon.extra_icons[0])
        else:
            wiki_text = ""

    lines: list[str] = old_text.split("\n")

    start: Optional[int] = None
    end: int = -1

    for index, line in enumerate(lines):
        if HEADER_PATTERN.match(line):
            if start is not None:
                end = index
                break
        if RENDERING_HEADER_PATTERN.match(line):
            start = index

    if start is not None:
        return (
            "\n".join(lines[: start + 2])
            + "\n"
            + wiki_text
            + "\n"
            + "\n".join(lines[end:])
        ), icons

    example_header: Optional[int] = None

    for index, line in enumerate(lines):
        if EXAMPLE_HEADER_PATTERN.match(line) or SEE_ALSO_HEADER_PATTERN.match(
            line
        ):
            example_header = index
            break

    if example_header is not None:
        return (
            "\n".join(lines[:example_header])
            + "\n"
            + "== Rendering ==\n\n=== [[Röntgen]] icons ===\n\n"
            + wiki_text
            + "\n"
            + "\n".join(lines[example_header:])
        ), icons

    return None, []
