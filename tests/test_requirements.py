"""
Check whether `requirements.txt` contains all requirements from `setup.py`.
"""
from map_machine import REQUIREMENTS
from pathlib import Path


def test_requirements() -> None:
    requirements: list[str]
    with Path("requirements.txt").open() as requirements_file:
        requirements = list(
            map(lambda x: x[:-1], requirements_file.readlines())
        )

    assert requirements == REQUIREMENTS
