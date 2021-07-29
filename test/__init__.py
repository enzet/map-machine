"""
Tests for Röntgen project.
"""
from pathlib import Path

from roentgen.icon import ShapeExtractor
from roentgen.scheme import Scheme

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

SCHEME: Scheme = Scheme(Path("scheme/default.yml"))
SHAPE_EXTRACTOR: ShapeExtractor = ShapeExtractor(
    Path("icons/icons.svg"), Path("icons/config.json")
)
