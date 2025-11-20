"""
Map Machine project dynamic metadata.
"""
from pathlib import Path

from setuptools import setup

__doc_url__ = "https://github.com/enzet/map-machine/blob/main/README.md"
__description__ = (
    "Simple Python map renderer for OpenStreetMap with custom icon set "
    "intended to display as many tags as possible"
)
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

with Path("README.md").open(encoding="utf-8") as input_file:
    long_description: str = input_file.read()

setup(
    name="map-machine",
    version="0.2.0",
    packages=[
        "map_machine",
        "map_machine.doc",
        "map_machine.element",
        "map_machine.feature",
        "map_machine.geometry",
        "map_machine.osm",
        "map_machine.pictogram",
        "map_machine.slippy",
        "map_machine.ui",
    ],
    url="https://github.com/enzet/map-machine",
    project_urls={
        "Bug Tracker": "https://github.com/enzet/map-machine/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    license="MIT",
    author="Sergey Vartanov",
    author_email="me@enzet.ru",
    description=__description__,
    long_description="Map Machine is a Python OpenStreetMap renderer and tile "
    "generator with a custom set of CC-BY 4.0 icons aimed to display as many "
    "map features as possible.\n\n"
    f"See [full documentation]({__doc_url__}).",
    long_description_content_type="text/markdown",
    entry_points={
        "console_scripts": ["map-machine=map_machine.main:main"],
    },
    package_data={
        "map_machine": [
            "icons/icons.svg",
            "icons/config.json",
            "icons/LICENSE",
            "scheme/default.yml",
        ],
    },
    python_requires=">=3.8",
    install_requires=REQUIREMENTS,
)
