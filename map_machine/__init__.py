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
__version__ = "0.2.0"

REQUIREMENTS = [
    "CairoSVG~=2.5.0",
    "colour~=0.1.5",
    "numpy~=1.24.4",
    "Pillow~=8.2.0",
    "portolan~=1.0.1",
    "PyYAML~=6.0.1",
    "Shapely~=1.7.1",
    "svgwrite~=1.4",
    "urllib3~=1.25.6",
]
