"""
Special icon collections for documentation.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import svgwrite
from svgwrite import Drawing
from svgwrite.text import Text
from svgwrite.shapes import Line, Rect

from map_machine.map_configuration import MapConfiguration
from map_machine.osm.osm_reader import Tags
from map_machine.pictogram.icon import ShapeExtractor, Icon, IconSet
from map_machine.scheme import Scheme
from map_machine.workspace import Workspace

WORKSPACE: Workspace = Workspace(Path("temp"))

SCHEME: Scheme = Scheme(WORKSPACE.DEFAULT_SCHEME_PATH)
EXTRACTOR: ShapeExtractor = ShapeExtractor(
    WORKSPACE.ICONS_PATH, WORKSPACE.ICONS_CONFIG_PATH
)


@dataclass
class Collection:
    """Icon collection."""

    page_name: str
    # Core tags
    tags: Tags
    # Tag key to be used in rows
    row_key: Optional[str] = None
    # List of tag values to be used in rows
    row_values: list[str] = field(default_factory=list)
    # Tag key to be used in columns
    column_key: Optional[str] = None
    # List of tag values to be used in columns
    column_values: list[str] = field(default_factory=list)

    def generate_wiki_table(self) -> tuple[str, list[Icon]]:
        """
        Generate Röntgen icon table for the OpenStreetMap wiki page.
        """
        icons: list[Icon] = []
        text: str = '{| class="wikitable"\n'

        if self.column_key is not None:
            text += f"! {{{{Key|{self.column_key}}}}}"
        else:
            text += "! Tag || Icon"

        if not self.column_values:
            self.column_values = [""]
        else:
            for column_value in self.column_values:
                text += " ||"
                if column_value:
                    text += (
                        " {{vert header|"
                        f"{{{{TagValue|{self.column_key}|{column_value}}}}}"
                        "}}"
                    )
        text += "\n"

        processed: set[str] = set()

        for row_value in self.row_values:
            text += "|-\n"
            if row_value:
                text += f"| {{{{Tag|{self.row_key}|{row_value}}}}}\n"
            else:
                text += "|\n"
            for column_value in self.column_values:
                current_tags: Tags = dict(self.tags) | {self.row_key: row_value}
                if column_value:
                    current_tags |= {self.column_key: column_value}
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


class SVGTable(Collection):
    """SVG table with icon combinations."""

    def __init__(
        self,
        svg: svgwrite.Drawing,
        page_name: str,
        tags: Tags,
        row_key: Optional[str] = None,
        row_values: list[str] = field(default_factory=list),
        column_key: Optional[str] = None,
        column_values: list[str] = field(default_factory=list),
    ):
        super().__init__(
            page_name, tags, row_key, row_values, column_key, column_values
        )

        self.svg: svgwrite.Drawing = svg

        self.border: np.ndarray = np.array((16.0, 16.0))
        self.step: float = 48.0
        self.icon_size: float = 32.0
        self.font_size: float = 10.0
        self.offset: float = 30.0
        self.half_step: np.ndarray = np.array(
            (self.step / 2.0, self.step / 2.0)
        )

        fonts: list[str] = [
            "JetBrains Mono",
            "Fira Code",
            "Fira Mono",
            "ui-monospace",
            "SFMono-regular",
            "SF Mono",
            "Menlo",
            "Consolas",
            "Liberation Mono",
            "monospace",
        ]
        self.font: str = ",".join(fonts)
        self.font_width: float = self.font_size * 0.7

        self.size: list[float] = [
            max(
                max(map(len, self.row_values)) * self.font_width,
                len(self.row_key) * self.font_width
                + (self.offset if self.column_values else 0),
            )
            if self.row_values
            else 25.0,
            max(map(len, self.column_values)) * self.font_width
            if self.column_values
            else 25.0,
        ]
        self.start_point: np.ndarray = (
            2 * self.border + np.array(self.size) + self.half_step
        )

    def draw_table(self) -> None:
        """Draw SVG table."""
        self.draw_rows()
        self.draw_columns()
        self.draw_delimiter()
        self.draw_rectangle()

        for i, row_value in enumerate(self.row_values):
            for j, column_value in enumerate(
                (self.column_values if self.column_values else [""])
            ):
                current_tags: Tags = dict(self.tags) | {self.row_key: row_value}
                if column_value:
                    current_tags |= {self.column_key: column_value}
                processed: set[str] = set()
                icon, _ = SCHEME.get_icon(
                    EXTRACTOR, current_tags, processed, MapConfiguration()
                )
                processed = icon.processed
                if not icon:
                    print("Icon was not constructed.")

                if (
                    icon.main_icon
                    and not icon.main_icon.is_default()
                    and (
                        not self.column_key
                        or not column_value
                        or (self.column_key in processed)
                    )
                    and (
                        not self.row_key
                        or not row_value
                        or (self.row_key in processed)
                    )
                ):
                    self.draw_icon(np.array((j, i)), icon)
                else:
                    self.draw_cross(np.array((j, i)))

        width, height = self.get_size()
        self.svg.update({"width": width, "height": height})

    def draw_rows(self) -> None:
        """Draw row texts."""
        point: np.ndarray = np.array(self.start_point) - np.array(
            (self.step / 2.0 + self.border[0], 0.0)
        )
        shift: np.ndarray = (
            -self.offset if self.column_values else 0.9,
            2.0 - self.step / 2.0 - self.border[1],
        )
        if self.row_key:
            self.draw_text(
                f"{self.row_key}=*",
                point + np.array(shift),
                anchor="end",
                weight="bold",
            )
        for row_value in self.row_values:
            if row_value:
                self.draw_text(
                    row_value, point + np.array((0.0, 2.0)), anchor="end"
                )
            point += np.array((0, self.step))

    def draw_columns(self) -> None:
        """Draw column texts."""
        point: np.ndarray = (
            self.start_point
            - self.half_step
            - self.border
            + np.array((0.0, 2.0 - self.offset))
        )
        if self.column_key:
            self.draw_text(
                f"{self.column_key}=*", point, anchor="end", weight="bold"
            )

        point = np.array(self.start_point)
        for column_value in self.column_values:
            text_point: np.ndarray = point + np.array(
                (2.0, -self.step / 2.0 - self.border[1])
            )
            self.draw_text(f"{column_value}", text_point, rotate=True)
            point += np.array((self.step, 0.0))

    def draw_delimiter(self) -> None:
        """Draw line between column and row titles."""
        if self.column_values:
            line: Line = self.svg.line(
                self.start_point - self.half_step - self.border,
                self.start_point
                - self.half_step
                - self.border
                - np.array((15, 15)),
                stroke_width=0.5,
                stroke="black",
            )
            self.svg.add(line)

    def draw_rectangle(self, color: str = "#FEA") -> None:
        """Draw rectangle beneath all cells."""
        rectangle: Rect = self.svg.rect(
            self.start_point - self.half_step,
            np.array((max(1, len(self.column_values)), len(self.row_values)))
            * self.step,
            fill=color,
        )
        self.svg.add(rectangle)

    def draw_icon(self, position: np.ndarray, icon: IconSet) -> None:
        """Draw icon in the table cell."""
        if not self.column_values:
            self.column_values = [""]
        point: np.ndarray = np.array(self.start_point) + position * self.step
        icon.main_icon.draw(self.svg, point, scale=self.icon_size / 16.0)

    def draw_text(
        self,
        text: str,
        point: np.ndarray,
        anchor: str = "start",
        weight: str = "normal",
        rotate: bool = False,
    ) -> None:
        """Draw text on the table."""
        text: Text = self.svg.text(
            text,
            point,
            font_family=self.font,
            font_size=self.font_size,
            text_anchor=anchor,
            font_weight=weight,
        )
        if rotate:
            text.update({"transform": f"rotate(270,{point[0]},{point[1]})"})
        self.svg.add(text)

    def draw_cross(self, position: np.ndarray, size: float = 15) -> None:
        """Draw cross in the cell."""
        point: np.ndarray = self.start_point + position * self.step
        for vector in np.array((1, 1)), np.array((1, -1)):
            line: Line = self.svg.line(
                point - size * vector,
                point + size * vector,
                stroke_width=0.5,
                stroke="black",
            )
            self.svg.add(line)

    def get_size(self) -> np.ndarray:
        """Get the whole picture size."""
        return (
            self.start_point
            + np.array((max(1, len(self.column_values)), len(self.row_values)))
            * self.step
            + self.border
        )


def draw_svg_tables(output_path: Path, html_file_path: Path) -> None:
    """Draw SVG tables of icon collections."""

    with Path("data/collections.json").open() as input_file:
        collections: list[list] = json.load(input_file)
        with html_file_path.open("w+") as html_file:
            for collection in collections:
                path: Path = output_path / f"{collection[0]}.svg"
                svg: Drawing = svgwrite.Drawing(path.name)

                row_key = collection[2] if len(collection) > 2 else None
                row_values = collection[3] if len(collection) > 3 else []
                column_key = collection[4] if len(collection) > 4 else None
                column_values = collection[5] if len(collection) > 5 else []

                table: SVGTable = SVGTable(
                    svg,
                    collection[0],
                    collection[1],
                    row_key,
                    row_values,
                    column_key,
                    column_values,
                )
                table.draw_table()

                with path.open("w+") as output_file:
                    svg.write(output_file)
                html_file.write(f'<img src="{path}" />\n')


if __name__ == "__main__":
    draw_svg_tables(Path("doc"), Path("result.html"))
