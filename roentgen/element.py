import logging
import sys
from pathlib import Path

import numpy as np
import svgwrite

from roentgen.workspace import workspace
from roentgen.icon import ShapeExtractor
from roentgen.point import Point
from roentgen.scheme import LineStyle, Scheme


def draw_element(options) -> None:
    """Draw single node, line, or area."""
    if options.node:
        target: str = "node"
        tags_description = options.node
    else:
        # Not implemented yet.
        sys.exit(1)

    tags: dict[str, str] = dict(
        [x.split("=") for x in tags_description.split(",")]
    )
    scheme: Scheme = Scheme(workspace.DEFAULT_SCHEME_PATH)
    extractor: ShapeExtractor = ShapeExtractor(
        workspace.ICONS_PATH, workspace.ICONS_CONFIG_PATH
    )
    processed: set[str] = set()
    icon, priority = scheme.get_icon(extractor, tags, processed)
    is_for_node: bool = target == "node"
    labels = scheme.construct_text(tags, "all", processed)
    point = Point(
        icon,
        labels,
        tags,
        processed,
        np.array((32, 32)),
        None,
        is_for_node=is_for_node,
        draw_outline=is_for_node,
    )
    border: np.array = np.array((16, 16))
    size: np.array = point.get_size() + border
    point.point = np.array((size[0] / 2, 16 / 2 + border[1] / 2))

    output_file_path: Path = workspace.output_path / "element.svg"
    svg = svgwrite.Drawing(str(output_file_path), size.astype(float))
    for style in scheme.get_style(tags):
        style: LineStyle
        path = svg.path(d="M 0,0 L 64,0 L 64,64 L 0,64 L 0,0 Z")
        path.update(style.style)
        svg.add(path)
    point.draw_main_shapes(svg)
    point.draw_extra_shapes(svg)
    point.draw_texts(svg)
    with output_file_path.open("w+") as output_file:
        svg.write(output_file)
    logging.info(f"Element is written to {output_file_path}.")
