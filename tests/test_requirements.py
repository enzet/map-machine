from map_machine import REQUIREMENTS
from pathlib import Path
from typing import List


def test_requirements() -> None:
    requirements: List[str]
    with Path("requirements.txt").open() as requirements_file:
        requirements = list(
            map(lambda x: x[:-1], requirements_file.readlines())
        )

    assert requirements == REQUIREMENTS
