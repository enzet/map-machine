"""
Test Fish shell completion.
"""
from map_machine.ui.completion import completion_commands


def test_completion() -> None:
    """Test Fish shell completion generation."""
    commands: str = completion_commands()
    assert commands.startswith("set -l")
