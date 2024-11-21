"""Moire markup extension for Map Machine."""

import argparse
from abc import ABC
from pathlib import Path
from typing import Any, Union

from moire.default import Default, DefaultHTML, DefaultMarkdown, DefaultWiki
from moire.moire import Tag

from map_machine.pictogram.icon import ShapeExtractor
from map_machine.ui import cli
from map_machine.ui.cli import COMMAND_LINES
from map_machine.workspace import workspace

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
    """Parser that stores arguments and creates help in Moire markup."""

    def __init__(self, *args, **kwargs) -> None:
        self.arguments: list[dict[str, Any]] = []
        super().__init__(*args, **kwargs)

    def add_argument(self, *args, **kwargs) -> None:
        """Just store argument with options."""
        super().add_argument(*args, **kwargs)
        argument: dict[str, Any] = {"arguments": args}
        argument |= kwargs

        self.arguments.append(argument)

    def get_moire_help(self) -> Tag:
        """Return Moire table with "Option" and "Description" columns."""
        table: Code = [[["Option"], ["Description"]]]

        for option in self.arguments:
            if option["arguments"][0] == "-h":
                continue

            array: Code = [
                [Tag("no_wrap", [Tag("m", [text])]), ", "]
                for text in option["arguments"]
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


class MapMachineMoire(Default, ABC):
    """Moire extension stub for Map Machine."""

    def osm(self, arg: Arguments) -> str:
        """OSM tag key or key–value pair of tag."""
        spec: str = self.clear(arg[0])
        if "=" in spec:
            key, tag = spec.split("=")
            return (
                self.get_ref_(f"{PREFIX}Key:{key}", self.m([key]))
                + " = "
                + self.get_ref_(f"{PREFIX}Tag:{key}={tag}", self.m([tag]))
            )

        return self.get_ref_(f"{PREFIX}Key:{spec}", self.m([spec]))

    def color(self, arg: Arguments) -> str:
        """Simple color sample."""
        raise NotImplementedError("color")

    def page_icon(self, arg: Arguments) -> str:
        """HTML page icon."""
        return ""

    def command(self, arg: Arguments) -> str:
        """Bash command from integration tests."""
        return "map-machine " + " ".join(COMMAND_LINES[self.clear(arg[0])])

    def icon(self, arg: Arguments) -> str:
        """Image with Röntgen icon."""
        raise NotImplementedError("icon")

    def options(self, arg: Arguments) -> str:
        """Table with option descriptions."""
        parser: ArgumentParser = ArgumentParser()
        command: str = self.clear(arg[0])
        if command == "render":
            cli.add_render_arguments(parser)
        elif command == "server":
            cli.add_server_arguments(parser)
        elif command == "tile":
            cli.add_tile_arguments(parser)
        elif command == "map":
            cli.add_map_arguments(parser)
        elif command == "element":
            cli.add_draw_arguments(parser)
        elif command == "mapcss":
            cli.add_mapcss_arguments(parser)
        else:
            raise NotImplementedError(
                "no separate function for parser creation"
            )
        return self.parse(parser.get_moire_help())

    def kbd(self, arg: Arguments) -> str:
        """Keyboard key."""
        return self.m(arg)

    def no_wrap(self, arg: Arguments) -> str:
        """Do not wrap text at white spaces."""
        return self.parse(arg[0])


class MapMachineHTML(MapMachineMoire, DefaultHTML):
    """Simple HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.images: dict = {}

    def table(self, arg: Arguments) -> str:
        """Simple table.  First row is treated as header."""
        content: str = ""
        cell: str = "".join(
            ["<th>" + self.parse(td, in_block=True) + "</th>" for td in arg[0]]
        )
        content += f"<tr>{cell}</tr>"
        for row in arg[1:]:
            cell: str = "".join(
                ["<td>" + self.parse(td, in_block=True) + "</td>" for td in row]
            )
            content += f"<tr>{cell}</tr>"
        return f"<table>{content}</table>"

    def color(self, arg: Arguments) -> str:
        """Simple color sample."""
        return (
            f'<span class="color" '
            f'style="background-color: {self.clear(arg[0])};"></span>'
        )

    def icon(self, arg: Arguments) -> str:
        """Image with Röntgen icon."""
        size: str = self.clear(arg[1]) if len(arg) > 1 else "16"
        return (
            f'<img class="icon" style="width: {size}px; height: {size}px;" '
            f'src="out/icons_by_id/{self.clear(arg[0])}.svg" />'
        )

    def kbd(self, arg: Arguments) -> str:
        """Keyboard key."""
        return f"<kbd>{self.clear(arg[0])}</kbd>"

    def page_icon(self, arg: Arguments) -> str:
        """HTML page icon."""
        return (
            f'<link rel="icon" type="image/svg" href="{self.clear(arg[0])}"'
            ' sizes="16x16">'
        )

    def no_wrap(self, arg: Arguments) -> str:
        """Do not wrap text at white spaces."""
        return f'<span style="white-space: nowrap;">{self.parse(arg[0])}</span>'

    def formal(self, arg: Arguments) -> str:
        """Formal variable."""
        return f'<span class="formal">{self.parse(arg[0])}</span>'


class MapMachineOSMWiki(MapMachineMoire, DefaultWiki):
    """
    Moire convertor to OpenStreetMap wiki markup.

    See https://wiki.openstreetmap.org/wiki/Main_Page
    """

    def __init__(self) -> None:
        super().__init__()
        self.images: dict = {}
        self.extractor: ShapeExtractor = ShapeExtractor(
            workspace.ICONS_PATH, workspace.ICONS_CONFIG_PATH
        )

    def osm(self, arg: Arguments) -> str:
        """Add special OSM tag key or key–value pair of tag."""
        spec: str = self.clear(arg[0])
        if "=" in spec:
            key, tag = spec.split("=")
            return f"{{{{Key|{key}|{tag}}}}}"

        return f"{{{{Tag|{spec}}}}}"

    def color(self, arg: Arguments) -> str:
        """Add color box on the wiki page with specified color."""
        return f"{{{{Color box|{self.clear(arg[0])}}}}}"

    def icon(self, arg: Arguments) -> str:
        """Process image with Röntgen icon."""
        size: str = self.clear(arg[1]) if len(arg) > 1 else "16"
        shape_id: str = self.clear(arg[0])
        name: str = self.extractor.get_shape(shape_id).name
        return f"[[File:Röntgen {name}.svg|{size}px]]"


class MapMachineMarkdown(MapMachineMoire, DefaultMarkdown):
    """GitHub flavored markdown."""

    images = {}

    def body(self, arg: Arguments) -> str:
        """Remove redundant new lines and add a warning."""
        return (
            "<!--\n"
            "    This is generated file.\n"
            "    Do not edit it manually, edit the Moire source file instead.\n"
            "-->\n\n"
            + self.parse(arg[0], in_block=True)
            .replace("\n\n\n", "\n\n")
            .replace("\n\n\n", "\n\n")
        )

    def color(self, arg: Arguments) -> str:
        """Ignore colors in Markdown."""
        return self.clear(arg[0])

    def icon(self, arg: Arguments) -> str:
        """Process image with Röntgen icon."""
        return f"[{self.clear(arg[0])}]"

    def kbd(self, arg: Arguments) -> str:
        """Process keyboard key."""
        return f"<kbd>{self.clear(arg[0])}</kbd>"

    def no_wrap(self, arg: Arguments) -> str:
        """Do not wrap text at white spaces."""
        return f'<span style="white-space: nowrap;">{self.parse(arg[0])}</span>'

    def formal(self, arg: Arguments) -> str:
        """Process formal variable."""
        return f"<{self.parse(arg[0])}>"


def convert(input_path: Path, output_path: Path) -> None:
    """Convert Moire file to Markdown."""
    with input_path.open(encoding="utf-8") as input_file:
        with output_path.open("w+", encoding="utf-8") as output_file:
            output_file.write(MapMachineMarkdown().convert(input_file.read()))


if __name__ == "__main__":
    for id_ in "readme", "contributing":
        convert(Path("doc") / "moi" / f"{id_}.moi", Path(f"{id_.upper()}.md"))
    convert(Path("doc") / "moi" / "install.moi", Path("doc") / "INSTALL.md")
