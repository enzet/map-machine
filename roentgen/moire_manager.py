"""
Moire markup extension for Röntgen.
"""
import argparse
from abc import ABC

from moire.moire import Tag
from moire.default import Default, DefaultHTML, DefaultMarkdown, DefaultWiki

from roentgen import workspace
from roentgen.icon import ShapeExtractor
from pathlib import Path
from typing import Dict, List, Any
import yaml

from roentgen.ui import add_render_arguments

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

Arguments = List[Any]

PREFIX: str = "https://wiki.openstreetmap.org/wiki/"


class ArgumentParser(argparse.ArgumentParser):
    """
    Argument parser that stores arguments and creates help in Moire markup.
    """

    def __init__(self, *args, **kwargs):
        self.arguments = []
        super(ArgumentParser, self).__init__(*args, **kwargs)

    def add_argument(self, *args, **kwargs) -> None:
        """Just store argument with options."""
        super(ArgumentParser, self).add_argument(*args, **kwargs)
        argument: Dict[str, Any] = {"arguments": [x for x in args]}

        for key in kwargs:
            argument[key] = kwargs[key]

        self.arguments.append(argument)

    def get_moire_help(self) -> Tag:
        """Return Moire table with stored arguments."""
        table = [[["Option"], ["Description"]]]

        for option in self.arguments:
            array = [[Tag("m", [x]), ", "] for x in option["arguments"]]
            row = [[x for y in array for x in y][:-1]]

            if "help" in option:
                help_value: List = [option["help"]]
                if (
                    "default" in option
                    and option["default"]
                    and option["default"] != "==SUPPRESS=="
                ):
                    help_value += [
                        ", default value: ",
                        Tag("m", [str(option["default"])]),
                    ]
                row.append(help_value)
            else:
                row.append([])
            table.append(row)
        return Tag("table", table)


class TestConfiguration:
    """
    GitHub Actions test configuration.
    """

    def __init__(self, test_config: Path):
        self.steps: Dict[str, Any] = {}

        with test_config.open() as input_file:
            content: Dict[str, Any] = yaml.load(
                input_file, Loader=yaml.FullLoader
            )
            steps: List[Dict[str, Any]] = content["jobs"]["build"]["steps"]
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

    def command(self, args: Arguments) -> str:
        """
        Bash command from GitHub Actions configuration.

        See .github/workflows/test.yml
        """
        return test_configuration.get_command(self.clear(args[0]))

    def icon(self, args: Arguments) -> str:
        raise NotImplementedError("icon")

    def options(self, args: Arguments) -> str:
        """Table with option descriptions."""
        parser: ArgumentParser = ArgumentParser()
        command: str = self.clear(args[0])
        if command == "render":
            add_render_arguments(parser)
        else:
            raise NotImplementedError(
                "no separate function for render creation"
            )
        return self.parse(parser.get_moire_help())


class RoentgenHTML(RoentgenMoire, DefaultHTML):
    """
    Simple HTML.
    """

    images = {}

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
            f'src="icons_by_id/{self.clear(args[0])}.svg" />'
        )


class RoentgenOSMWiki(RoentgenMoire, DefaultWiki):
    """
    OpenStreetMap wiki.

    See https://wiki.openstreetmap.org/wiki/Main_Page
    """

    images = {}
    extractor = ShapeExtractor(
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
