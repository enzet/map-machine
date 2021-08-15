import os
import subprocess
from pathlib import Path
from typing import List

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def rasterize(from_: Path, to_: Path, area: str = "", dpi: float = 90) -> None:
    """
    Make PNG image out of SVG using Inkscape.
    """
    inkscape: str = "inkscape"
    if "INKSCAPE_BIN" in os.environ:
        inkscape: str = os.environ["INKSCAPE_BIN"]

    commands: List[str] = [inkscape]
    commands += ["--export-png", to_.absolute()]
    commands += ["--export-dpi", str(dpi)]
    if area:
        commands += ["--export-area", area]
    commands += [from_.absolute()]

    subprocess.run(commands)
