"""
Creating fish shell autocompletion commands.

See https://fishshell.com/docs/current/completions.html
"""

import argparse
from pathlib import Path
from typing import Any

from map_machine.ui import cli
from map_machine.ui.cli import COMMANDS


class ArgumentParser(argparse.ArgumentParser):
    """Argument parser that generates fish shell autocompletion commands."""

    def __init__(self, *args, **kwargs) -> None:
        self.arguments: list[dict[str, Any]] = []
        super().__init__(*args, **kwargs)

    def add_argument(self, *args, **kwargs) -> None:
        """Just store argument with options."""
        super().add_argument(*args, **kwargs)
        argument: dict[str, Any] = {"arguments": args}
        argument |= kwargs

        self.arguments.append(argument)

    def get_complete(self, command: str) -> str:
        """Return fish complete command."""
        result: str = ""

        for argument in self.arguments:
            result += "complete -c map-machine"
            result += f' -n "__fish_seen_subcommand_from {command}"'
            if len(argument["arguments"]) == 2:
                result += f" -s {argument['arguments'][0][1:]}"
                result += f" -l {argument['arguments'][1][2:]}"
            else:
                result += f" -l {argument['arguments'][0][2:]}"
            if "help" in argument:
                result += f' -d "{argument["help"]}"'
            result += "\n"

        return result


def completion_commands() -> str:
    """Print fish completion commands."""
    commands: str = " ".join(COMMANDS)
    result: str = ""
    result += f"set -l commands {commands}\n"
    result += "complete -c map-machine -f\n"
    result += (
        f'complete -c map-machine -n "not __fish_seen_subcommand_from '
        f'$commands" -a "{commands}"\n'
    )
    for command in COMMANDS:
        if command in ["icons", "taginfo"]:
            continue
        parser: ArgumentParser = ArgumentParser()
        if command == "render":
            cli.add_render_arguments(parser)
            cli.add_map_arguments(parser)
        elif command == "server":
            cli.add_server_arguments(parser)
        elif command == "tile":
            cli.add_tile_arguments(parser)
            cli.add_map_arguments(parser)
        elif command == "element":
            cli.add_draw_arguments(parser)
        elif command == "mapcss":
            cli.add_mapcss_arguments(parser)
        else:
            raise NotImplementedError(
                f"no separate function for parser creation for {command}"
            )
        result += parser.get_complete(command) + "\n"

    return result


if __name__ == "__main__":
    completions_path: Path = (
        Path.home() / ".config/fish/completions/map-machine.fish"
    )
    with completions_path.open("w+") as output_file:
        output_file.write(completion_commands())
