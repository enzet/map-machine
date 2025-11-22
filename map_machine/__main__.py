"""Map Machine entry point."""

import sys

from map_machine.main import main

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

if __name__ == "__main__":
    PYTHON_MAJOR_VERSION: int = 3
    PYTHON_MINOR_VERSION: int = 9

    if (
        sys.version_info.major < PYTHON_MAJOR_VERSION
        or sys.version_info.minor < PYTHON_MINOR_VERSION
    ):
        sys.exit(1)

    main()
