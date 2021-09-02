"""
Röntgen project dynamic metadata.
"""
from setuptools import setup

setup(
    name="roentgen-map",
    version="0.1.0",
    packages=["roentgen"],
    url="https://github.com/enzet/Roentgen",
    project_urls={
        "Bug Tracker": "https://github.com/enzet/Roentgen/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    license="MIT",
    author="Sergey Vartanov",
    author_email="me@enzet.ru",
    description="Python renderer for OpenStreetMap with custom icon set",
    long_description="Röntgen is a Python OpenStreetMap renderer and tile "
    "generator with a custom set of CC-BY 4.0 icons aimed to display as many "
    "map features as possible.",
    entry_points={
        "console_scripts": ["roentgen=roentgen.main:main"],
    },
    python_requires=">=3.9",
)
