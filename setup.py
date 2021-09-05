"""
Röntgen project dynamic metadata.
"""
from pathlib import Path

from setuptools import setup
from roentgen import (
    __author__,
    __description__,
    __doc_url__,
    __email__,
    __url__,
    __version__,
)

with Path("README.md").open() as input_file:
    long_description: str = input_file.read()

setup(
    name="roentgen-map",
    version=__version__,
    packages=["roentgen"],
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
    long_description="Röntgen is a Python OpenStreetMap renderer and tile "
    "generator with a custom set of CC-BY 4.0 icons aimed to display as many "
    "map features as possible.\n\n"
    f"See [full documentation]({__doc_url__}).",
    long_description_content_type="text/markdown",
    entry_points={
        "console_scripts": ["roentgen=roentgen.main:main"],
    },
    package_data={
        "roentgen": [
            "icons/icons.svg",
            "icons/config.json",
            "icons/LICENSE",
            "scheme/default.yml",
        ],
    },
    python_requires=">=3.9",
    install_requires=[
        "CairoSVG>=2.5.0",
        "colour>=0.1.5",
        "numpy>=1.18.1",
        "Pillow>=8.2.0",
        "portolan>=1.0.1",
        "pycairo",
        "pytest>=6.2.2",
        "PyYAML>=4.2b1",
        "svgwrite>=1.4",
        "urllib3>=1.25.6",
    ],
)
