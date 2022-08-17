"""Map Machine: Python map renderer for OpenStreetMap with custom icon set."""

__project__ = "Map Machine"
__description__ = (
    "Simple Python map renderer for OpenStreetMap with custom icon set "
    "intended to display as many tags as possible"
)
__url__ = "https://github.com/enzet/map-machine"
__doc_url__ = f"{__url__}/blob/main/README.md"
__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"
__version__ = "0.1.7"

from pathlib import Path

with Path("requirements.txt").open() as input_file:
    REQUIREMENTS: list[str] = [x[:-1] for x in input_file.readlines()]
