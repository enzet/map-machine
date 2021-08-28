"""
Moire markup extension for Röntgen.
"""
import argparse
from abc import ABC
from pathlib import Path
from typing import Any, Union

import yaml
from moire.default import Default, DefaultHTML, DefaultMarkdown, DefaultWiki
from moire.moire import Tag

from roentgen import ui
from roentgen.icon import ShapeExtractor
from roentgen.workspace import workspace

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

Arguments = list[Any]
Code = Union[str, Tag, list]

PREFIX: str = "https://wiki.openstreetmap.org/wiki/"


def parse_text(text: str, margins: str, tag_id: str) -> Code:
    """Parse formal arguments."""
    word: str = ""
    result: Code = []
    inside: bool = False

    for character in text:
        if character not in margins:
            word += character
            continue
        if word:
            result.append(Tag(tag_id, [word]) if inside else word)
        word = ""
        inside = not inside

    if word:
        result.append(word)

    return result


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

    def get_moire_help(self) -> Tag:
        """
        Return Moire table with "Option" and "Description" columns filled with
        arguments.
        """
        table: Code = [[["Option"], ["Description"]]]

        for option in self.arguments:
            if option["arguments"][0] == "-h":
                continue

            array: Code = [
                [Tag("no_wrap", [Tag("m", [x])]), ", "]
                for x in option["arguments"]
            ]
            cell: Code = [x for y in array for x in y][:-1]
            if "metavar" in option:
                cell += [
                    " ",
                    Tag("m", [parse_text(option["metavar"], "<>", "formal")]),
                ]
            row: Code = [cell]

            if "help" in option:
                help_value: list = parse_text(option["help"], "`", "m")
                if (
                    "default" in option
                    and option["default"]
                    and option["default"] != "==SUPPRESS=="
                ):
                    if (
                        "action" in option
                        and option["action"] == argparse.BooleanOptionalAction
                    ):
                        if option["default"] is True:
                            help_value += [", set by default"]
                        elif option["default"] is False:
                            help_value += [", not set by default"]
                    else:
                        default_value: Code = Tag("m", [str(option["default"])])
                        if "type" in option and option["type"] in [int, float]:
                            default_value = str(option["default"])
                        help_value += [", default value: ", default_value]
                row.append(help_value)
            else:
                row.append([])

            table.append(row)

        return Tag("table", table)


class TestConfiguration:
    """
    GitHub Actions test configuration.
    """

    def __init__(self, test_config: Path) -> None:
        self.steps: dict[str, Any] = {}

        with test_config.open() as input_file:
            content: dict[str, Any] = yaml.load(
                input_file, Loader=yaml.FullLoader
            )
            steps: list[dict[str, Any]] = content["jobs"]["build"]["steps"]
            for step in steps:
                if "name" not in step:
                    continue
                self.steps[step["name"]] = step

    def get_command(self, name: str) -> str:
        """Get shell script commands for the test."""
        return self.steps[name]["run"].strip()


test_configuration: TestConfiguration = TestConfiguration(
    workspace.GITHUB_TEST_PATH
)


class RoentgenMoire(Default, ABC):
    """
    Moire extension stub for Röntgen.
    """

    def osm(self, args: Arguments) -> str:
        """OSM tag key or key–value pair of tag."""
        spec: str = self.clear(args[0])
        if "=" in spec:
            key, tag = spec.split("=")
            return (
                self.get_ref_(f"{PREFIX}Key:{key}", self.m([key]))
                + "="
                + self.get_ref_(f"{PREFIX}Tag:{key}={tag}", self.m([tag]))
            )
        else:
            return self.get_ref_(f"{PREFIX}Key:{spec}", self.m([spec]))

    def color(self, args: Arguments) -> str:
        """Simple color sample."""
        raise NotImplementedError("color")

    def page_icon(self, args: Arguments) -> str:
        """HTML page icon."""
        return ""

    def command(self, args: Arguments) -> str:
        """
        Bash command from GitHub Actions configuration.

        See .github/workflows/test.yml
        """
        return test_configuration.get_command(self.clear(args[0]))

    def icon(self, args: Arguments) -> str:
        """Image with Röntgen icon."""
        raise NotImplementedError("icon")

    def options(self, args: Arguments) -> str:
        """Table with option descriptions."""
        parser: ArgumentParser = ArgumentParser()
        command: str = self.clear(args[0])
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
                "no separate function for parser creation"
            )
        return self.parse(parser.get_moire_help())

    def kbd(self, args: Arguments) -> str:
        """Keyboard key."""
        return self.m(args)

    def no_wrap(self, args: Arguments) -> str:
        """Do not wrap text at white spaces."""
        return self.parse(args[0])


class RoentgenHTML(RoentgenMoire, DefaultHTML):
    """
    Simple HTML.
    """

    def __init__(self) -> None:
        super().__init__()
        self.images: dict = {}

    def table(self, arg: Arguments) -> str:
        """Simple table.  First row is treated as header."""
        content: str = ""
        cell: str = "".join(
            ["<th>" + self.parse(td, inblock=True) + "</th>" for td in arg[0]]
        )
        content += f"<tr>{cell}</tr>"
        for tr in arg[1:]:
            cell: str = "".join(
                ["<td>" + self.parse(td, inblock=True) + "</td>" for td in tr]
            )
            content += f"<tr>{cell}</tr>"
        return f"<table>{content}</table>"

    def color(self, args: Arguments) -> str:
        """Simple color sample."""
        return (
            f'<span class="color" '
            f'style="background-color: {self.clear(args[0])};"></span>'
        )

    def icon(self, args: Arguments) -> str:
        """Image with Röntgen icon."""
        size: str = self.clear(args[1]) if len(args) > 1 else 16
        return (
            f'<img class="icon" style="width: {size}px; height: {size}px;" '
            f'src="out/icons_by_id/{self.clear(args[0])}.svg" />'
        )

    def kbd(self, args: Arguments) -> str:
        """Keyboard key."""
        return f"<kbd>{self.clear(args[0])}</kbd>"

    def page_icon(self, args: Arguments) -> str:
        """HTML page icon."""
        return (
            f'<link rel="icon" type="image/svg" href="{self.clear(args[0])}"'
            ' sizes="16x16">'
        )

    def no_wrap(self, args: Arguments) -> str:
        """Do not wrap text at white spaces."""
        return (
            f'<span style="white-space: nowrap;">{self.parse(args[0])}</span>'
        )

    def formal(self, args: Arguments) -> str:
        """Formal variable."""
        return f'<span class="formal">{self.parse(args[0])}</span>'


class RoentgenOSMWiki(RoentgenMoire, DefaultWiki):
    """
    OpenStreetMap wiki.

    See https://wiki.openstreetmap.org/wiki/Main_Page
    """

    def __init__(self) -> None:
        super().__init__()
        self.images: dict = {}
        self.extractor: ShapeExtractor = ShapeExtractor(
            workspace.ICONS_PATH, workspace.ICONS_CONFIG_PATH
        )

    def osm(self, args: Arguments) -> str:
        """OSM tag key or key–value pair of tag."""
        spec: str = self.clear(args[0])
        if "=" in spec:
            key, tag = spec.split("=")
            return f"{{{{Key|{key}|{tag}}}}}"
        else:
            return f"{{{{Tag|{spec}}}}}"

    def color(self, args: Arguments) -> str:
        """Simple color sample."""
        return f"{{{{Color box|{self.clear(args[0])}}}}}"

    def icon(self, args: Arguments) -> str:
        """Image with Röntgen icon."""
        size: str = self.clear(args[1]) if len(args) > 1 else 16
        shape_id: str = self.clear(args[0])
        name: str = self.extractor.get_shape(shape_id).name
        return f"[[File:Röntgen {name}.svg|{size}px]]"


class RoentgenMarkdown(RoentgenMoire, DefaultMarkdown):
    """
    GitHub flavored markdown.
    """

    images = {}

    def color(self, args: Arguments) -> str:
        """Simple color sample."""
        return self.clear(args[0])

    def icon(self, args: Arguments) -> str:
        """Image with Röntgen icon."""
        return f"[{self.clear(args[0])}]"

    def kbd(self, args: Arguments) -> str:
        """Keyboard key."""
        return f"<kbd>{self.clear(args[0])}</kbd>"

    def no_wrap(self, args: Arguments) -> str:
        """Do not wrap text at white spaces."""
        return (
            f'<span style="white-space: nowrap;">{self.parse(args[0])}</span>'
        )

    def formal(self, args: Arguments) -> str:
        """Formal variable."""
        return f"<{self.parse(args[0])}>"
