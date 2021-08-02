"""
MapCSS scheme creation.
"""
from pathlib import Path
from typing import List, Optional, Dict

import logging
from colour import Color

from roentgen import workspace
from roentgen.grid import IconCollection
from roentgen.icon import ShapeExtractor
from roentgen.osm_reader import STAGES_OF_DECAY
from roentgen.scheme import Scheme, Matcher


class MapCSSWriter:
    def __init__(
        self,
        scheme: Scheme,
        icon_directory_name: str,
        add_icons_for_lifecycle: bool,
    ):
        self.add_icons_for_lifecycle = add_icons_for_lifecycle
        self.icon_directory_name = icon_directory_name

        self.point_matchers: List[Matcher] = scheme.node_matchers
        self.line_matchers: List[Matcher] = scheme.way_matchers

    def add_selector(
        self,
        target: str,
        matcher: Matcher,
        prefix: str = "",
        opacity: Optional[float] = None,
    ) -> str:
        elements: Dict[str, str] = {}

        clean_shapes = matcher.get_clean_shapes()
        if clean_shapes:
            elements["icon-image"] = (
                f'"{self.icon_directory_name}/'
                + "___".join(clean_shapes)
                + '.svg"'
            )

            if opacity is not None:
                elements["icon-opacity"] = f"{opacity:.2f}"

        style = matcher.get_style()
        if style:
            if "fill" in style:
                elements["fill-color"] = style["fill"]
            if "stroke" in style:
                elements["color"] = style["stroke"]
            if "stroke-width" in style:
                elements["width"] = style["stroke-width"]
            if "stroke-dasharray" in style:
                elements["dashes"] = style["stroke-dasharray"]
            if "opacity" in style:
                elements["fill-opacity"] = style["opacity"]
                elements["opacity"] = style["opacity"]

        if not elements:
            return ""

        selector: str = target + matcher.get_mapcss_selector(prefix) + " {\n"
        for element in elements:
            selector += f"    {element}: {elements[element]};\n"
        selector += "}\n"

        return selector

    def write(self, output_file) -> None:
        """
        Construct icon selectors for MapCSS 0.2 scheme.
        """
        with workspace.MAPCSS_PART_FILE_PATH.open() as input_file:
            output_file.write(input_file.read())

        output_file.write("\n")

        for line_matcher in self.line_matchers:
            for target in ["way", "relation"]:
                output_file.write(self.add_selector(target, line_matcher))

        for matcher in self.point_matchers:
            for target in ["node", "area"]:
                output_file.write(self.add_selector(target, matcher))

        if not self.add_icons_for_lifecycle:
            return

        for index, stage_of_decay in enumerate(STAGES_OF_DECAY):
            opacity: float = 0.6 - 0.4 * index / (len(STAGES_OF_DECAY) - 1)
            for matcher in self.point_matchers:
                if len(matcher.tags) > 1:
                    continue
                for target in ["node", "area"]:
                    output_file.write(
                        self.add_selector(
                            target, matcher, stage_of_decay, opacity
                        )
                    )


def write_mapcss() -> None:
    """
    Write MapCSS 0.2 scheme.
    """
    directory: Path = workspace.get_mapcss_path()
    icons_with_outline_path: Path = workspace.get_mapcss_icons_path()

    scheme: Scheme = Scheme(workspace.DEFAULT_SCHEME_PATH)
    extractor: ShapeExtractor = ShapeExtractor(
        workspace.ICONS_PATH, workspace.ICONS_CONFIG_PATH
    )
    collection: IconCollection = IconCollection.from_scheme(scheme, extractor)
    collection.draw_icons(
        icons_with_outline_path, color=Color("black"), outline=True
    )
    mapcss_writer: MapCSSWriter = MapCSSWriter(
        scheme, workspace.MAPCSS_ICONS_DIRECTORY_NAME, True
    )
    with workspace.get_mapcss_file_path().open("w+") as output_file:
        mapcss_writer.write(output_file)

    logging.info(f"MapCSS 0.2 scheme is written to {directory}.")
