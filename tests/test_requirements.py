from map_machine import REQUIREMENTS
from pathlib import Path


def test_requirements() -> None:
    with Path("requirements.txt").open() as requirements_file:
        assert [x[:-1] for x in requirements_file.readlines()] == REQUIREMENTS
