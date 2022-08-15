"""Drawing separate map elements."""
import argparse
import logging
from pathlib import Path

import numpy as np
import svgwrite
from svgwrite.path import Path as SVGPath

from map_machine.element.grid import Grid
from map_machine.map_configuration import LabelMode, MapConfiguration
from map_machine.osm.osm_reader import Tags
from map_machine.pictogram.icon import ShapeExtractor
from map_machine.pictogram.point import Point
from map_machine.scheme import LineStyle, Scheme
from map_machine.text import Label, TextConstructor
from map_machine.workspace import workspace

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def draw_node(tags: Tags) -> None:
    grid: Grid = Grid()
    grid.add_node(tags, 0, 0)
    grid.draw(Path("out.svg"))


def draw_element(options: argparse.Namespace) -> None:
    """Draw single node, line, or area."""
    target: str
    tags_description: str
    if options.node:
        target = "node"
        tags_description = options.node
    elif options.way:
        target = "way"
        tags_description = options.way
    else:
        target = "area"
        tags_description = options.area

    tags: dict[str, str] = {
        tag.split("=")[0]: tag.split("=")[1]
        for tag in tags_description.split(",")
    }
    scheme: Scheme = Scheme.from_file(workspace.DEFAULT_SCHEME_PATH)
    extractor: ShapeExtractor = ShapeExtractor(
        workspace.ICONS_PATH, workspace.ICONS_CONFIG_PATH
    )
    processed: set[str] = set()
    icon, _ = MapConfiguration(scheme).get_icon(extractor, tags, processed)
    is_for_node: bool = target == "node"
    text_constructor: TextConstructor = TextConstructor(scheme)
    labels: list[Label] = text_constructor.construct_text(
        tags, processed, LabelMode.ALL
    )
    point: Point = Point(
        icon,
        labels,
        tags,
        processed,
        np.array((32.0, 32.0)),
        is_for_node=is_for_node,
        draw_outline=is_for_node,
    )
    border: np.ndarray = np.array((16.0, 16.0))
    size: np.ndarray = point.get_size() + border
    point.point = np.array((size[0] / 2.0, 16.0 / 2.0 + border[1] / 2.0))

    output_file_path: Path = workspace.output_path / "element.svg"
    svg: svgwrite.Drawing = svgwrite.Drawing(
        str(output_file_path), size.astype(float)
    )
    for style in scheme.get_style(tags):
        style: LineStyle
        path: SVGPath = svg.path(d="M 0,0 L 64,0 L 64,64 L 0,64 L 0,0 Z")
        path.update(style.style)
        svg.add(path)
    point.draw_main_shapes(svg)
    point.draw_extra_shapes(svg)
    point.draw_texts(svg)
    with output_file_path.open("w+", encoding="utf-8") as output_file:
        svg.write(output_file)
    logging.info(f"Element is written to {output_file_path}.")
