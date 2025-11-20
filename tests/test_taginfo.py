"""Test Taginfo project generation."""

from pathlib import Path

from map_machine.doc.taginfo import TaginfoProjectFile
from tests import SCHEME


def test_taginfo() -> None:
    """Test Taginfo project generation."""
    output_file_path: Path = Path("temp") / "taginfo.json"

    project_file: TaginfoProjectFile = TaginfoProjectFile(
        output_file_path, SCHEME
    )
    assert project_file.structure["project"]["name"] == "Map Machine"
