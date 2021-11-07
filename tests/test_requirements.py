"""
Check whether `requirements.txt` contains all requirements from `setup.py`.
"""
from pathlib import Path

from map_machine import REQUIREMENTS


def test_requirements() -> None:
    """Test whether `requirements.txt` has the same packages as `setup.py`."""
    requirements: list[str]
    with Path("requirements.txt").open(encoding="utf-8") as requirements_file:
        requirements = list(
            map(lambda x: x[:-1], requirements_file.readlines())
        )

    assert requirements == REQUIREMENTS
