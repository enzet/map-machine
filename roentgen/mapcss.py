"""
MapCSS scheme creation.
"""
from pathlib import Path
from typing import Dict, List

import logging
from colour import Color

from roentgen.grid import IconCollection
from roentgen.icon import ShapeExtractor
from roentgen.scheme import Scheme


def construct_selectors(scheme: Scheme, icon_directory_name: str) -> str:
    """
    Construct icon selectors for MapCSS 0.2 scheme.
    """
    selectors: Dict[str, List[str]] = {}
    for matcher in scheme.node_matchers:
        if matcher.shapes and not matcher.location_restrictions:
            # TODO: support location restrictions
            selectors[matcher.get_mapcss_selector()] = [
                (x if isinstance(x, str) else x["shape"])
                for x in matcher.shapes
            ]

    s: str = ""
    for selector in selectors:
        for target in ["node", "area"]:
            s += (
                target + selector + " {\n"
                f'    icon-image: "{icon_directory_name}/'
                + "___".join(selectors[selector])
                + '.svg";\n}\n'
            )
    return s


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
    with Path("data/roentgen_icons_part.mapcss").open() as input_file:
        header = input_file.read()

    with (directory / "roentgen_icons.mapcss").open("w+") as output_file:
        output_file.write(header)
        output_file.write("\n")
        output_file.write(construct_selectors(scheme, icon_directory_name))

    logging.info(f"MapCSS 0.2 scheme is written to {directory}.")
