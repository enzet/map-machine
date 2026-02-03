"""Tests for Map Machine project."""

from pathlib import Path

from map_machine.scheme import Scheme
from map_machine.workspace import Workspace

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

workspace: Workspace = Workspace(Path("temp"))


SCHEME: Scheme = Scheme.from_file(workspace.DEFAULT_SCHEME_PATH)
