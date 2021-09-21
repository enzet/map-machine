"""
Drawing separate map elements.
"""
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Set

import numpy as np
import svgwrite
from svgwrite.path import Path as SVGPath

from map_machine.icon import ShapeExtractor
from map_machine.point import Point
from map_machine.scheme import LineStyle, Scheme
from map_machine.text import Label
from map_machine.workspace import workspace

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


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

    tags: Dict[str, str] = dict(
        [x.split("=") for x in tags_description.split(",")]
    )
    scheme: Scheme = Scheme(workspace.DEFAULT_SCHEME_PATH)
    extractor: ShapeExtractor = ShapeExtractor(
        workspace.ICONS_PATH, workspace.ICONS_CONFIG_PATH
    )
    processed: Set[str] = set()
    icon, priority = scheme.get_icon(extractor, tags, processed)
    is_for_node: bool = target == "node"
    labels: List[Label] = scheme.construct_text(tags, "all", processed)
    point: Point = Point(
        icon,
        labels,
        tags,
        processed,
        np.array((32, 32)),
        is_for_node=is_for_node,
        draw_outline=is_for_node,
    )
    border: np.ndarray = np.array((16, 16))
    size: np.ndarray = point.get_size() + border
    point.point = np.array((size[0] / 2, 16 / 2 + border[1] / 2))

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
    with output_file_path.open("w+") as output_file:
        svg.write(output_file)
    logging.info(f"Element is written to {output_file_path}.")
