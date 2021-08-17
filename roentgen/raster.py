"""
Rasterize vector graphics using Inkscape.
"""
import logging
import os
import subprocess
from pathlib import Path
from typing import List

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

INKSCAPE_BIN: str = "INKSCAPE_BIN"


def rasterize(from_: Path, to_: Path, area: str = "", dpi: float = 90) -> None:
    """
    Make PNG image out of SVG using Inkscape.

    See https://inkscape.org/
    """
    if "INKSCAPE_BIN" not in os.environ:
        logging.fatal(
            f"Environment variable {INKSCAPE_BIN} not set. Please, install "
            f"Inkscape and set the variable to be able to rasterize SVG files."
        )

    commands: List[str] = [os.environ[INKSCAPE_BIN]]
    commands += ["--export-png", to_.absolute()]
    commands += ["--export-dpi", str(dpi)]
    if area:
        commands += ["--export-area", area]
    commands += [from_.absolute()]

    logging.info(f"Rasterize SVG file to {to_}...")
    subprocess.run(commands)
