"""
Automate OpenStreetMap wiki editing.
"""
import re
from pathlib import Path
from typing import Optional

from map_machine.map_configuration import MapConfiguration
from map_machine.osm.osm_reader import Tags
from map_machine.pictogram.icon import ShapeExtractor
from map_machine.scheme import Scheme
from map_machine.workspace import Workspace

WORKSPACE: Workspace = Workspace(Path("temp"))

SCHEME: Scheme = Scheme(WORKSPACE.DEFAULT_SCHEME_PATH)
EXTRACTOR: ShapeExtractor = ShapeExtractor(
    WORKSPACE.ICONS_PATH, WORKSPACE.ICONS_CONFIG_PATH
)

HEADER_PATTERN: re.Pattern = re.compile("==?=?.*==?=?")
SEE_ALSO_HEADER_PATTERN: re.Pattern = re.compile("==\\s*See also\\s*==")
EXAMPLE_HEADER_PATTERN: re.Pattern = re.compile("==\\s*Example\\s*==")
RENDERING_HEADER_PATTERN: re.Pattern = re.compile(
    "===\\s*\\[\\[Röntgen]] icons\\s*==="
)


def generate_table(
    tags: Tags,
    row_key: str,
    row_values: list[str],
    column_key: str,
    column_values: list[str],
) -> str:
    """
    Generate Röntgen icon table for the OpenStreetMap wiki page.

    :param tags: core tags
    :param row_key: tag key to be used in rows
    :param row_values: list of tag values to be used in rows
    :param column_key: tag key to be used in columns
    :param column_values: list of tag values to be used in columns
    """
    text: str = '{| class="wikitable"\n'

    if column_key is not None:
        text += f"! {{{{Key|{column_key}}}}}"
    else:
        text += "! Tag || Icon"

    if not column_values:
        column_values = [""]
    else:
        for column_value in column_values:
            text += " ||"
            if column_value:
                text += (
                    " {{vert header|"
                    f"{{{{TagValue|{column_key}|{column_value}}}}}"
                    "}}"
                )
    text += "\n"

    processed: set[str] = set()

    for row_value in row_values:
        text += "|-\n"
        if row_value:
            text += f"| {{{{Tag|{row_key}|{row_value}}}}}\n"
        else:
            text += "|\n"
        for column_value in column_values:
            current_tags: Tags = dict(tags) | {row_key: row_value}
            if column_value:
                current_tags |= {column_key: column_value}
            icon, _ = SCHEME.get_icon(
                EXTRACTOR, current_tags, processed, MapConfiguration()
            )
            if not icon:
                print("Icon was not constructed.")
            text += (
                f"| [[Image:Röntgen {icon.main_icon.get_name()}.svg|32px]]\n"
            )

    text += "|}\n"

    return text


def generate_new_text(
    old_text: str,
    tags: Tags,
    row_key: str,
    row_values: list[str],
    column_key: str,
    column_values: list[str],
) -> Optional[str]:
    """
    Generate Röntgen icon table for the OpenStreetMap wiki page.

    :param old_text: previous wiki page text
    :param tags: core tags
    :param row_key: tag key to be used in rows
    :param row_values: list of tag values to be used in rows
    :param column_key: tag key to be used in columns
    :param column_values: list of tag values to be used in columns
    :return: new wiki page text
    """
    wiki_text: str

    if row_key:
        wiki_text = generate_table(
            tags, row_key, row_values, column_key, column_values
        )
    else:
        processed = set()
        icon, _ = SCHEME.get_icon(
            EXTRACTOR, tags, processed, MapConfiguration()
        )
        if icon.main_icon.is_default():
            wiki_text = (
                f"Röntgen icon set has additional icon for the tag: "
                f"[[Image:Röntgen {icon.extra_icons[0].get_name()}.svg|32px]]."
                f"\n"
            )
        else:
            wiki_text = (
                f"[[Image:Röntgen {icon.main_icon.get_name()}.svg|32px]]\n"
            )

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
        )

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
        )

    return None
