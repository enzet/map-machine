"""Special icon collections for documentation."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np
import svgwrite
from svgwrite import Drawing
from svgwrite.shapes import Line, Rect
from svgwrite.text import Text

from map_machine.map_configuration import MapConfiguration
from map_machine.osm.osm_reader import Tags
from map_machine.pictogram.icon import ShapeExtractor, IconSet
from map_machine.scheme import Scheme
from map_machine.workspace import Workspace

WORKSPACE: Workspace = Workspace(Path("temp"))

SCHEME: Scheme = Scheme.from_file(WORKSPACE.DEFAULT_SCHEME_PATH)
EXTRACTOR: ShapeExtractor = ShapeExtractor(
    WORKSPACE.ICONS_PATH, WORKSPACE.ICONS_CONFIG_PATH
)
MONOSPACE_FONTS: list[str] = [
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


@dataclass
class Collection:
    """Icon collection."""

    # Core tags.
    tags: Tags

    # Tag key to be used in rows.
    row_key: Optional[str] = None

    # List of tag values to be used in rows.
    row_values: list[str] = field(default_factory=list)

    # Tag key to be used in columns.
    column_key: Optional[str] = None

    # List of tag values to be used in columns.
    column_values: list[str] = field(default_factory=list)

    # List of tags to be used in rows.
    row_tags: list[Tags] = field(default_factory=list)

    @classmethod
    def deserialize(cls, structure: dict[str, Any]):
        """Deserialize icon collection from structure."""
        return cls(
            structure["tags"],
            structure.get("row_key", None),
            structure.get("row_values", []),
            structure.get("column_key", None),
            structure.get("column_values", []),
            structure.get("row_tags", []),
        )


class SVGTable:
    """SVG table with icon combinations."""

    def __init__(self, collection: Collection, svg: svgwrite.Drawing):
        self.collection: Collection = collection
        self.svg: svgwrite.Drawing = svg

        self.border: np.ndarray = np.array((16.0, 16.0))
        self.step: float = 48.0
        self.icon_size: float = 32.0
        self.font_size: float = 10.0
        self.offset: float = 30.0
        self.half_step: np.ndarray = np.array(
            (self.step / 2.0, self.step / 2.0)
        )
        self.font: str = ",".join(MONOSPACE_FONTS)
        self.font_width: float = self.font_size * 0.7

        self.size: list[float] = [
            (
                max(
                    max(map(len, self.collection.row_values)) * self.font_width,
                    len(self.collection.row_key) * self.font_width
                    + (self.offset if self.collection.column_values else 0),
                    170.0,
                )
                if self.collection.row_values
                else 0.0
            ),
            (
                max(map(len, self.collection.column_values)) * self.font_width
                if self.collection.column_values
                else 0.0
            ),
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

        for i, row_value in enumerate(self.collection.row_values):
            for j, column_value in enumerate(
                (
                    self.collection.column_values
                    if self.collection.column_values
                    else [""]
                )
            ):
                current_tags: Tags = dict(self.collection.tags) | {
                    self.collection.row_key: row_value
                }
                if column_value:
                    current_tags |= {self.collection.column_key: column_value}
                processed: set[str] = set()
                icon, _ = MapConfiguration(SCHEME).get_icon(
                    EXTRACTOR, current_tags, processed
                )
                processed = icon.processed
                if not icon:
                    print("Icon was not constructed.")

                if (
                    icon.main_icon
                    and not icon.main_icon.is_default()
                    and (
                        not self.collection.column_key
                        or not column_value
                        or (self.collection.column_key in processed)
                    )
                    and (
                        not self.collection.row_key
                        or not row_value
                        or (self.collection.row_key in processed)
                    )
                ):
                    self.draw_icon(np.array((j, i)), icon)
                else:
                    self.draw_cross(np.array((j, i)))

        width, height = self.get_size()
        self.svg.elements.insert(
            0, self.svg.rect((0, 0), (width, height), fill="white")
        )
        self.svg.update({"width": width, "height": height})

    def draw_rows(self) -> None:
        """Draw row texts."""
        point: np.ndarray = np.array(self.start_point) - np.array(
            (self.step / 2.0 + self.border[0], 0.0)
        )
        shift: np.ndarray = (
            -self.offset if self.collection.column_values else 0.9,
            2.0 - self.step / 2.0 - self.border[1],
        )
        if self.collection.row_key:
            self.draw_text(
                f"{self.collection.row_key}=*",
                point + np.array(shift),
                anchor="end",
                weight="bold",
            )
        for row_value in self.collection.row_values:
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
        if self.collection.column_key:
            self.draw_text(
                f"{self.collection.column_key}=*",
                point,
                anchor="end",
                weight="bold",
            )

        point = np.array(self.start_point)
        for column_value in self.collection.column_values:
            text_point: np.ndarray = point + np.array(
                (2.0, -self.step / 2.0 - self.border[1])
            )
            self.draw_text(f"{column_value}", text_point, rotate=True)
            point += np.array((self.step, 0.0))

    def draw_delimiter(self) -> None:
        """Draw line between column and row titles."""
        if self.collection.column_values:
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
            np.array(
                (
                    max(1, len(self.collection.column_values)),
                    len(self.collection.row_values),
                )
            )
            * self.step,
            fill=color,
        )
        self.svg.add(rectangle)

    def draw_icon(self, position: np.ndarray, icon: IconSet) -> None:
        """Draw icon in the table cell."""
        if not self.collection.column_values:
            self.collection.column_values = [""]
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
            + np.array(
                (
                    max(1, len(self.collection.column_values)),
                    len(self.collection.row_values),
                )
            )
            * self.step
            - self.half_step
            + self.border
        )


def draw_svg_tables(output_path: Path, html_file_path: Path) -> None:
    """Draw SVG tables of icon collections."""

    with (Path("data") / "collections.json").open() as input_file:
        collections: list[dict[str, Any]] = json.load(input_file)

        with html_file_path.open("w+") as html_file:
            for structure in collections:
                if "id" not in structure:
                    continue

                path: Path = output_path / f"{structure['id']}.svg"
                svg: Drawing = svgwrite.Drawing(path.name)

                collection: Collection = Collection.deserialize(structure)

                table: SVGTable = SVGTable(collection, svg)
                table.draw_table()

                with path.open("w+") as output_file:
                    svg.write(output_file)
                html_file.write(
                    f'<img src="{path}" style="border: 1px solid #DDD;" />\n'
                )


if __name__ == "__main__":
    draw_svg_tables(Path("doc"), Path("out") / "collections.html")
