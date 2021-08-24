"""
Röntgen project dynamic metadata.
"""
from setuptools import setup

setup(
    name="roentgen-map",
    version="0.1",
    packages=["roentgen"],
    url="https://github.com/enzet/Roentgen",
    license="MIT",
    author="Sergey Vartanov",
    author_email="me@enzet.ru",
    description="Python renderer for OpenStreetMap with custom icon set",
    entry_points={
        "console_scripts": ["roentgen=roentgen.main:main"],
    },
    python_requires=">=3.9",
)
