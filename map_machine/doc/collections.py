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


class SVGTable:
    """SVG table with icon combinations."""

    def __init__(self, svg):
        self.svg = svg

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

    def draw_cross(self, point):
        for vector in np.array((1, 1)), np.array((1, -1)):
            line = self.svg.line(
                point - 15 * vector,
                point + 15 * vector,
                stroke_width=0.5,
                stroke="black",
            )
            self.svg.add(line)


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
        table = SVGTable(svg)

        border: np.ndarray = np.array((16.0, 16.0))
        step: float = 48.0
        icon_size: float = 32.0
        font_size: float = 10.0
        offset: float = 30.0
        half_step: np.ndarray = np.array((step / 2.0, step / 2.0))

        fonts: list[str] = [
            "JetBrains Mono",
            "Fira Code",
            "Fira Mono",
            "monospace",
        ]
        font: str = ",".join(fonts)
        font_width: float = font_size * 0.62

        size: list[float] = [
            max(
                max(map(len, self.row_values)) * font_width,
                (len(self.row_key) + 2) * font_width
                + (offset if self.column_values else 0),
            )
            if self.row_values
            else 25.0,
            max(map(len, self.column_values)) * font_width
            if self.column_values
            else 25.0,
        ]

        start_point: np.ndarray = 2 * border + np.array(size) + half_step
        point = np.array(start_point) - np.array((step / 2.0 + border[0], 0.0))
        shift = (
            -offset if self.column_values else 0,
            2.0 - step / 2.0 - border[1],
        )

        if self.row_key:
            table.draw_bold_text(f"{self.row_key}=*", point + np.array(shift))

        if self.column_key:
            table.draw_bold_text(
                f"{self.column_key}=*",
                point + np.array((0.0, 2.0 - step / 2.0 - border[0] - offset)),
            )

        for row_value in self.row_values:
            if row_value:
                table.draw_text(row_value, point + np.array((0.0, 2.0)))
            point += np.array((0, step))

        if self.column_values:
            line = svg.line(
                start_point - half_step - border,
                start_point - half_step - border - np.array((15, 15)),
                stroke_width=0.5,
                stroke="black",
            )
            svg.add(line)

        if not self.column_values:
            self.column_values = [""]

        rectangle = svg.rect(
            start_point - half_step,
            np.array((len(self.column_values), len(self.row_values))) * step,
            fill="#fea",
        )
        svg.add(rectangle)

        point = np.array(start_point)

        for column_value in self.column_values:
            text_point = point + np.array((2, -step / 2.0 - border[1]))
            text = svg.text(
                f"{column_value}",
                text_point,
                font_family=font,
                font_size=font_size,
                transform=f"rotate(270,{text_point[0]},{text_point[1]})",
            )
            svg.add(text)
            point += np.array((step, 0.0))

        point = np.array(start_point)

        last = None

        for row_value in self.row_values:
            for column_value in self.column_values:
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
                    icon.main_icon.draw(svg, point, scale=icon_size / 16.0)
                else:
                    table.draw_cross(point)
                last = np.array(point)
                point += np.array((step, 0.0))
            point = np.array((start_point[0], point[1] + step))

        if last is None:
            return point
        else:
            return last + np.array((step / 2, step / 2)) + border


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
