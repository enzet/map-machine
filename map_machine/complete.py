import argparse
from typing import Any

from map_machine import ui
from map_machine.ui import COMMANDS


class ArgumentParser(argparse.ArgumentParser):
    """
    Argument parser that stores arguments and creates help in Moire markup.
    """

    def __init__(self, *args, **kwargs) -> None:
        self.arguments: list[dict[str, Any]] = []
        super(ArgumentParser, self).__init__(*args, **kwargs)

    def add_argument(self, *args, **kwargs) -> None:
        """Just store argument with options."""
        super(ArgumentParser, self).add_argument(*args, **kwargs)
        argument: dict[str, Any] = {"arguments": [x for x in args]}

        for key in kwargs:
            argument[key] = kwargs[key]

        self.arguments.append(argument)

    def get_complete(self, command: str) -> str:
        """
        Return Moire table with "Option" and "Description" columns filled with
        arguments.
        """
        s = ""

        for argument in self.arguments:
            s += "complete -c map-machine"
            s += f' -n "__fish_seen_subcommand_from {command}"'
            if len(argument["arguments"]) == 2:
                s += f" -s {argument['arguments'][0][1:]}"
                s += f" -l {argument['arguments'][1][2:]}"
            else:
                s += f" -l {argument['arguments'][0][2:]}"
            if "help" in argument:
                s += f" -d \"{argument['help']}\""
            s += "\n"

        return s


if __name__ == "__main__":
    commands: str = " ".join(COMMANDS)
    print(f"set -l commands {commands}")
    print("complete -c map-machine -f")
    print(
        f'complete -c map-machine -n "not __fish_seen_subcommand_from '
        f'$commands" -a "{commands}"'
    )

    for command in COMMANDS:
        if command in ["icons", "taginfo"]:
            continue
        parser: ArgumentParser = ArgumentParser()
        if command == "render":
            ui.add_render_arguments(parser)
            ui.add_map_arguments(parser)
        elif command == "server":
            ui.add_server_arguments(parser)
        elif command == "tile":
            ui.add_tile_arguments(parser)
            ui.add_map_arguments(parser)
        elif command == "element":
            ui.add_element_arguments(parser)
        elif command == "mapcss":
            ui.add_mapcss_arguments(parser)
        else:
            raise NotImplementedError(
                f"no separate function for parser creation for {command}"
            )
        print(parser.get_complete(command))
