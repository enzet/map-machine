"""
Test Fish shell completion.
"""
from map_machine.ui.completion import completion_commands


def test_completion() -> None:
    commands: str = completion_commands()
    assert commands.startswith("set -l")
