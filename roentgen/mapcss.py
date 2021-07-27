"""
MapCSS scheme creation.
"""
from pathlib import Path
from typing import Dict, List, Optional

import logging
from colour import Color

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

        self.matchers: Dict[Matcher, List[str]] = {}
        for matcher in scheme.node_matchers:
            if matcher.shapes and not matcher.location_restrictions:
                self.matchers[matcher] = [
                    (x if isinstance(x, str) else x["shape"])
                    for x in matcher.shapes
                ]

    def add_selector(
        self,
        target: str,
        matcher: Matcher,
        prefix: str = "",
        opacity: Optional[float] = None,
    ) -> str:
        selector = (
            target + matcher.get_mapcss_selector(prefix) + " {\n"
            f'    icon-image: "{self.icon_directory_name}/'
            + "___".join(self.matchers[matcher])
            + '.svg";\n'
        )
        if opacity is not None:
            selector += f"    icon-opacity: {opacity:.2f};\n"
        selector += "}\n"
        return selector

    def write(self, output_file) -> None:
        """
        Construct icon selectors for MapCSS 0.2 scheme.
        """
        with Path("data/roentgen_icons_part.mapcss").open() as input_file:
            output_file.write(input_file.read())

        output_file.write("\n")

        for matcher in self.matchers:
            for target in ["node", "area"]:
                output_file.write(self.add_selector(target, matcher))

        if not self.add_icons_for_lifecycle:
            return

        for index, stage_of_decay in enumerate(STAGES_OF_DECAY):
            opacity: float = 0.6 - 0.4 * index / (len(STAGES_OF_DECAY) - 1)
            for matcher in self.matchers:
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
    icon_directory_name: str = "icons"

    out_path: Path = Path("out")
    directory: Path = out_path / "roentgen_icons_mapcss"
    directory.mkdir(exist_ok=True)
    icons_with_outline_path: Path = directory / icon_directory_name

    icons_with_outline_path.mkdir(parents=True, exist_ok=True)

    scheme: Scheme = Scheme(Path("scheme/default.yml"))
    extractor: ShapeExtractor = ShapeExtractor(
        Path("icons/icons.svg"), Path("icons/config.json")
    )
    collection: IconCollection = IconCollection.from_scheme(scheme, extractor)
    collection.draw_icons(
        icons_with_outline_path, color=Color("black"), outline=True
    )
    mapcss_writer: MapCSSWriter = MapCSSWriter(
        scheme, icon_directory_name, True
    )
    with (directory / "roentgen_icons.mapcss").open("w+") as output_file:
        mapcss_writer.write(output_file)

    logging.info(f"MapCSS 0.2 scheme is written to {directory}.")
