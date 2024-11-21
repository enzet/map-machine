"""
Map Machine project dynamic metadata.
"""

from pathlib import Path

from setuptools import setup
from map_machine import (
    __author__,
    __description__,
    __doc_url__,
    __email__,
    __url__,
    __version__,
    REQUIREMENTS,
)

with Path("README.md").open(encoding="utf-8") as input_file:
    long_description: str = input_file.read()

setup(
    name="map-machine",
    version=__version__,
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
    url=__url__,
    project_urls={
        "Bug Tracker": f"{__url__}/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    license="MIT",
    author=__author__,
    author_email=__email__,
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
    python_requires=">=3.9",
    install_requires=REQUIREMENTS,
)
