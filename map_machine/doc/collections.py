"""
Special icon collections for documentation.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import svgwrite
from svgwrite import Drawing

from map_machine.map_configuration import MapConfiguration
from map_machine.osm.osm_reader import Tags
from map_machine.pictogram.icon import ShapeExtractor, Icon
from map_machine.scheme import Scheme
from map_machine.workspace import Workspace

WORKSPACE: Workspace = Workspace(Path("temp"))

SCHEME: Scheme = Scheme(WORKSPACE.DEFAULT_SCHEME_PATH)
EXTRACTOR: ShapeExtractor = ShapeExtractor(
    WORKSPACE.ICONS_PATH, WORKSPACE.ICONS_CONFIG_PATH
)


@dataclass
class SVGTable:
    """SVG table with icon combinations."""

    def __init__(self, svg, row_key, row_values, column_key, column_values):
        self.svg = svg

        self.row_key = row_key
        self.row_values = row_values
        self.column_key = column_key
        self.column_values = column_values

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

    def draw(self):
        """Draw rows and columns."""
        self.draw_rows()
        self.draw_columns()
        self.draw_delimiter()
        self.draw_rectangle()

    def draw_rows(self):
        """Draw row texts."""
        point = np.array(self.start_point) - np.array(
            (self.step / 2.0 + self.border[0], 0.0)
        )
        shift = (
            -self.offset if self.column_values else 0,
            2.0 - self.step / 2.0 - self.border[1],
        )
        if self.row_key:
            self.draw_bold_text(f"{self.row_key}=*", point + np.array(shift))
        for row_value in self.row_values:
            if row_value:
                self.draw_text(row_value, point + np.array((0.0, 2.0)))
            point += np.array((0, self.step))

    def draw_columns(self):
        """Draw column texts."""
        point = np.array(self.start_point) - np.array(
            (self.step / 2.0 + self.border[0], 0.0)
        )
        if self.column_key:
            self.draw_bold_text(
                f"{self.column_key}=*",
                point
                + np.array(
                    (0.0, 2.0 - self.step / 2.0 - self.border[0] - self.offset)
                ),
            )

        point = np.array(self.start_point)
        for column_value in self.column_values:
            text_point = point + np.array(
                (2, -self.step / 2.0 - self.border[1])
            )
            text = self.svg.text(
                f"{column_value}",
                text_point,
                font_family=self.font,
                font_size=self.font_size,
                transform=f"rotate(270,{text_point[0]},{text_point[1]})",
            )
            self.svg.add(text)
            point += np.array((self.step, 0.0))

    def draw_delimiter(self):
        if self.column_values:
            line = self.svg.line(
                self.start_point - self.half_step - self.border,
                self.start_point
                - self.half_step
                - self.border
                - np.array((15, 15)),
                stroke_width=0.5,
                stroke="black",
            )
            self.svg.add(line)

    def draw_rectangle(self):
        rectangle = self.svg.rect(
            self.start_point - self.half_step,
            np.array((max(1, len(self.column_values)), len(self.row_values)))
            * self.step,
            fill="#fea",
        )
        self.svg.add(rectangle)

    def draw_icon(self, position, icon):
        if not self.column_values:
            self.column_values = [""]
        point = np.array(self.start_point) + position * self.step
        icon.main_icon.draw(self.svg, point, scale=self.icon_size / 16.0)

    def draw_text(self, text, point):
        text = self.svg.text(
            text,
            point,
            font_family=self.font,
            font_size=self.font_size,
            text_anchor="end",
        )
        self.svg.add(text)

    def draw_bold_text(self, text, point):
        text = self.svg.text(
            text,
            point,
            font_family=self.font,
            font_size=self.font_size,
            font_weight="bold",
            text_anchor="end",
        )
        self.svg.add(text)

    def draw_cross(self, position: np.ndarray, size: float = 15):
        point = self.start_point + position * self.step
        for vector in np.array((1, 1)), np.array((1, -1)):
            line = self.svg.line(
                point - size * vector,
                point + size * vector,
                stroke_width=0.5,
                stroke="black",
            )
            self.svg.add(line)

    def get_size(self):
        return (
            self.start_point
            + np.array((max(1, len(self.column_values)), len(self.row_values)))
            * self.step
            + self.border
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

    def generate_table(self) -> tuple[str, list[Icon]]:
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

    def draw_table(self, svg: Drawing):
        """Draw SVG table."""
        table = SVGTable(
            svg,
            self.row_key + "=*" if self.row_key else None,
            self.row_values,
            self.column_key + "=*" if self.column_key else None,
            self.column_values,
        )
        table.draw()

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
                    table.draw_icon(np.array((j, i)), icon)
                else:
                    table.draw_cross(np.array((j, i)))

        return table.get_size()


tower_type_values: list[str] = [
    "communication",
    "lighting",
    "monitoring",
    "siren",
]

collections = [
    Collection(
        "Tag:man_made=mast",
        {"man_made": "mast"},
        "tower:construction",
        ["freestanding", "lattice", "guyed_tube", "guyed_lattice"],
        "tower:type",
        [""] + tower_type_values,
    ),
    Collection(
        "Tag:natural=volcano",
        {"natural": "volcano"},
        "volcano:type",
        ["stratovolcano", "shield", "scoria"],
        "volcano:status",
        ["", "active", "dormant", "extinct"],
    ),
    Collection(
        "Tag:tower:construction=guyed_tube",
        {"man_made": "mast", "tower:construction": "guyed_tube"},
        "tower:type",
        [""] + tower_type_values,
    ),
    Collection(
        "Tag:tower:construction=guyed_lattice",
        {"man_made": "mast", "tower:construction": "guyed_lattice"},
        "tower:type",
        [""] + tower_type_values,
    ),
    Collection(
        "Key:communication:mobile_phone",
        {"communication:mobile_phone": "yes"},
    ),
    Collection(
        "Key:traffic_calming",
        {},
        "traffic_calming",
        [
            "bump",
            "mini_bumps",
            "hump",
            "table",
            "cushion",
            "rumble_strip",
            "dip",
            "double_dip",
            # "dynamic_bump", "chicane",
            # "choker", "island", "chocked_island", "chocked_table",
        ],
    ),
    Collection(
        "Key:crane:type",
        {"man_made": "crane"},
        "crane:type",
        [
            "gantry_crane",
            "floor-mounted_crane",
            "portal_crane",
            "travel_lift",
            "tower_crane",
        ],
    ),
    Collection(
        "Tag:tower:type=diving",
        {"man_made": "tower", "tower:type": "diving"},
    ),
    Collection(
        "Key:design",
        {},
        "power",
        ["tower", "pole"],
        "design",
        [
            "one-level",
            "two-level",
            "three-level",
            "four-level",
            "donau",
            "donau_inverse",
            "barrel",
            "asymmetric",
            "triangle",
            "flag",
            "delta",
            "delta_two-level",
            "delta_three-level",
            "y-frame",
            "x-frame",
            "h-frame",
            "guyed_h-frame",
            "portal",
            "portal_two-level",
            "portal_three-level",
        ],
    ),
]


def main() -> None:
    with Path("result.html").open("w+") as html_file:
        for collection in collections:
            path: Path = Path("doc") / f"{collection.page_name}.svg"
            svg: svgwrite = svgwrite.Drawing(path.name)
            width, height = collection.draw_table(svg)
            svg.update({"width": width, "height": height})
            with path.open("w+") as output_file:
                svg.write(output_file)
            html_file.write(f'<img src="doc/{path.name}" />\n')


if __name__ == "__main__":
    main()
