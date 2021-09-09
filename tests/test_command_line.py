"""
Test command line commands.
"""
from subprocess import PIPE, Popen

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def error_run(arguments: list[str], message: bytes) -> None:
    """Run command that should fail and check error message."""
    p = Popen(["map-machine"] + arguments, stderr=PIPE)
    _, error = p.communicate()
    assert p.returncode != 0
    assert error == message


def run(arguments: list[str], message: bytes) -> None:
    """Run command that should fail and check error message."""
    p = Popen(["map-machine"] + arguments, stderr=PIPE)
    _, error = p.communicate()
    assert p.returncode == 0
    assert error == message
