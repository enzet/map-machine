"""Test command line commands."""

from pathlib import Path
from subprocess import PIPE, Popen

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

from typing import TYPE_CHECKING

from defusedxml import ElementTree

from map_machine.element.element import draw_element
from map_machine.ui.cli import COMMAND_LINES, parse_arguments

if TYPE_CHECKING:
    import argparse

LOG: bytes = (
    b"INFO Constructing ways...\n"
    b"INFO Constructing nodes...\n"
    b"INFO Drawing ways...\n"
    b"INFO Drawing main icons...\n"
    b"INFO Drawing extra icons...\n"
    b"INFO Drawing texts...\n"
)
OUTPUT_PATH: Path = Path("out")


def error_run(arguments: list[str], message: bytes) -> None:
    """Run command that should fail and check error message."""
    command: list[str] = ["map-machine", *arguments]
    with Popen(command, stderr=PIPE) as pipe:  # noqa: S603
        _, output = pipe.communicate()
        assert output == message
        assert pipe.returncode != 0


def run(arguments: list[str], message: bytes) -> None:
    """Run command that should not fail and check output."""
    command: list[str] = ["map-machine", *arguments]
    with Popen(command, stderr=PIPE) as pipe:  # noqa: S603
        _, output = pipe.communicate()
        assert output == message
        assert pipe.returncode == 0


class TestOSMFile:
    """Test OSM file."""

    def __init__(self) -> None:
        self.id_: int = 1
        self.content: str = ""

    def add_node(
        self,
        tags: dict[str, str],
        latitude: float = 20.0005,
        longitude: float = 10.0005,
    ) -> "TestOSMFile":
        """Add a test node with given tags."""
        self.content += (
            f' <node id="{self.id_}" visible="true" version="1" changeset="1" '
            f'timestamp="2000-01-01T00:00:00Z" user="Temp" uid="{self.id_}" '
            f'lat="{latitude}" lon="{longitude}">\n'
        )
        self.id_ += 1

        for key, value in tags.items():
            self.content += f'  <tag k="{key}" v="{value}"/>\n'

        self.content += " </node>\n"

        return self

    def add_way(self, tags: dict[str, str]) -> "TestOSMFile":
        """Add a test way with two arbitrary nodes."""

        id_1: int = self.id_
        self.add_node({}, 20.0, 10.0)

        id_2: int = self.id_
        self.add_node({}, 20.001, 10.001)

        self.content += (
            f' <way id="{self.id_}" visible="true" version="1" changeset="1" '
            f'timestamp="2000-01-01T00:00:00Z" user="Temp" uid="{self.id_}">\n'
        )
        self.content += f'  <nd ref="{id_1}"/>\n'
        self.content += f'  <nd ref="{id_2}"/>\n'

        for key, value in tags.items():
            self.content += f'  <tag k="{key}" v="{value}"/>\n'

        self.content += " </way>\n"
        self.id_ += 1

        return self

    def write(self, file_path: Path) -> None:
        """Create a test OSM file."""
        with file_path.open("w") as file:
            file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            file.write('<osm version="0.6">\n')
            file.write(
                ' <bounds minlat="20.0000000" minlon="10.0000000" '
                'maxlat="20.0010000" maxlon="10.0010000"/>\n'
            )
            file.write(self.content)
            file.write("</osm>\n")


def test_wrong_render_arguments() -> None:
    """Test `render` command with wrong arguments."""
    error_run(
        ["render", "-z", "17"],
        b"CRITICAL Specify either --input, or --bounding-box, or "
        b"--coordinates.\n",
    )


def test_render_coordinates() -> None:
    """Test `render` command without input file."""
    run(
        COMMAND_LINES["render"] + ["--cache", "tests/data"],
        LOG + b"INFO Writing output SVG to `out/map.svg`...\n",
    )
    with (OUTPUT_PATH / "map.svg").open(encoding="utf-8") as output_file:
        root = ElementTree.parse(output_file).getroot()

    # 8 expected elements: `defs`, `rect` (background), `g` (outline),
    # `g` (icon), 4 `text` elements (credits).
    expected_elements: int = 8

    assert len(root) == expected_elements
    assert len(root[3][0]) == 0
    assert root.get("width") == "186.0"
    assert root.get("height") == "198.0"


def test_render_file() -> None:
    """Test `render` command with input file."""
    run(
        COMMAND_LINES["render"]
        + ["--cache", "tests/data", "--input", "tests/data/tree.osm"],
        LOG + b"INFO Writing output SVG to `out/map.svg`...\n",
    )
    with (OUTPUT_PATH / "map.svg").open(encoding="utf-8") as output_file:
        root = ElementTree.parse(output_file).getroot()

    # 8 expected elements: `defs`, `rect` (background), `g` (outline),
    # `g` (icon), 4 `text` elements (credits).
    expected_elements: int = 8

    assert len(root) == expected_elements
    assert len(root[3][0]) == 0
    assert root.get("width") == "186.0"
    assert root.get("height") == "198.0"


def test_render_with_tooltips() -> None:
    """Test `render` command."""
    run(
        COMMAND_LINES["render"] + ["--cache", "tests/data", "--tooltips"],
        LOG + b"INFO Writing output SVG to `out/map.svg`...\n",
    )
    with (OUTPUT_PATH / "map.svg").open(encoding="utf-8") as output_file:
        root = ElementTree.parse(output_file).getroot()

    # 8 expected elements: `defs`, `rect` (background), `g` (outline),
    # `g` (icon), 4 `text` elements (credits).
    expected_elements: int = 8

    assert len(root) == expected_elements
    assert len(root[3][0]) == 1
    assert root[3][0][0].text == "natural: tree"
    assert root.get("width") == "186.0"
    assert root.get("height") == "198.0"


def test_render_with_simple_roads() -> None:
    """Test `render` command with normal roads."""

    temp_file_path: Path = OUTPUT_PATH / "temp.osm"

    osm_file: TestOSMFile = TestOSMFile()
    osm_file.add_way({"highway": "primary"})
    osm_file.write(temp_file_path)

    run(
        COMMAND_LINES["render"]
        + [
            "--cache",
            "tests/data",
            "--roads",
            "simple",
            "--input",
            str(temp_file_path),
        ],
        LOG + b"INFO Writing output SVG to `out/map.svg`...\n",
    )
    with (OUTPUT_PATH / "map.svg").open(encoding="utf-8") as output_file:
        root = ElementTree.parse(output_file).getroot()

    # 8 expected elements: `defs`, `rect` (background), `path` (outline),
    # `path` (road), 4 `text` elements (credits).
    expected_elements: int = 8

    assert len(root) == expected_elements
    assert root[2].tag == "{http://www.w3.org/2000/svg}path"
    assert root[3].tag == "{http://www.w3.org/2000/svg}path"


def test_render_with_lanes_roads() -> None:
    """Test `render` command with lanes roads."""

    temp_file_path: Path = OUTPUT_PATH / "temp.osm"

    osm_file: TestOSMFile = TestOSMFile()
    osm_file.add_way({"highway": "primary", "lanes": "2"})
    osm_file.write(temp_file_path)

    run(
        COMMAND_LINES["render"]
        + [
            "--cache",
            "tests/data",
            "--roads",
            "lanes",
            "--input",
            str(temp_file_path),
        ],
        LOG + b"INFO Writing output SVG to `out/map.svg`...\n",
    )
    with (OUTPUT_PATH / "map.svg").open(encoding="utf-8") as output_file:
        root = ElementTree.parse(output_file).getroot()

    # 8 expected elements: `defs`, `rect` (background), `path` (outline),
    # `path` (road), `path` (lanes), 4 `text` elements (credits).
    expected_elements: int = 9

    assert len(root) == expected_elements
    assert root[2].tag == "{http://www.w3.org/2000/svg}path"
    assert root[3].tag == "{http://www.w3.org/2000/svg}path"
    assert root[4].tag == "{http://www.w3.org/2000/svg}path"


def test_icons() -> None:
    """Test `icons` command."""
    run(
        COMMAND_LINES["icons"],
        b"INFO Icons are written to `out/icons_by_name` and "
        b"`out/icons_by_id`.\n"
        b"INFO Icon grid is written to `out/icon_grid.svg`.\n"
        b"INFO Icon grid is written to `doc/grid.svg`.\n",
    )
    assert (OUTPUT_PATH / "icon_grid.svg").is_file()
    assert (OUTPUT_PATH / "icons_by_name").is_dir()
    assert (OUTPUT_PATH / "icons_by_id").is_dir()
    assert (OUTPUT_PATH / "icons_by_name" / "Röntgen apple.svg").is_file()
    assert (OUTPUT_PATH / "icons_by_id" / "apple.svg").is_file()


def test_mapcss() -> None:
    """Test `mapcss` command."""
    run(
        COMMAND_LINES["mapcss"],
        b"INFO MapCSS 0.2 scheme is written to `out/map_machine_mapcss`.\n",
    )
    out_path: Path = OUTPUT_PATH / "map_machine_mapcss"

    assert out_path.is_dir()
    assert (out_path / "icons" / "apple.svg").is_file()
    assert (out_path / "map_machine.mapcss").is_file()
    assert (out_path / "icons" / "LICENSE").is_file()


def test_draw() -> None:
    """Test `draw` command."""
    run(
        COMMAND_LINES["draw"],
        LOG + b"INFO Map is drawn to `out/element.svg`.\n",
    )
    assert (OUTPUT_PATH / "element.svg").is_file()


def test_unwrapped_draw() -> None:
    """Test `element` command from inside the project."""
    arguments: argparse.Namespace = parse_arguments(
        ["map_machine"] + COMMAND_LINES["draw"]
    )
    draw_element(arguments)


def test_tile() -> None:
    """Test `tile` command."""
    run(
        COMMAND_LINES["tile"] + ["--cache", "tests/data"],
        LOG + b"INFO Tile is drawn to `out/tiles/tile_18_160199_88904.svg`.\n"
        b"INFO SVG file is rasterized to "
        b"`out/tiles/tile_18_160199_88904.png`.\n",
    )

    assert (OUTPUT_PATH / "tiles" / "tile_18_160199_88904.svg").is_file()
    assert (OUTPUT_PATH / "tiles" / "tile_18_160199_88904.png").is_file()
