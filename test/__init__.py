"""
Tests for Röntgen project.
"""
from pathlib import Path

from roentgen.icon import ShapeExtractor
from roentgen.scheme import Scheme
from roentgen.workspace import Workspace

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

workspace: Workspace = Workspace(Path("temp"))

SCHEME: Scheme = Scheme(workspace.DEFAULT_SCHEME_PATH)
SHAPE_EXTRACTOR: ShapeExtractor = ShapeExtractor(
    workspace.ICONS_PATH, workspace.ICONS_CONFIG_PATH
)
