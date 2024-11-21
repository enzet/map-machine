"""Test command line commands."""

import argparse
from pathlib import Path
from subprocess import PIPE, Popen

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

from xml.etree import ElementTree
from xml.etree.ElementTree import Element

from map_machine.ui.cli import COMMAND_LINES, parse_arguments

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
    with Popen(["map-machine"] + arguments, stderr=PIPE) as pipe:
        _, output = pipe.communicate()
        assert output == message
        assert pipe.returncode != 0


def run(arguments: list[str], message: bytes) -> None:
    """Run command that should not fail and check output."""
    with Popen(["map-machine"] + arguments, stderr=PIPE) as pipe:
        _, output = pipe.communicate()
        assert output == message
        assert pipe.returncode == 0


def test_wrong_render_arguments() -> None:
    """Test `render` command with wrong arguments."""
    error_run(
        ["render", "-z", "17"],
        b"CRITICAL Specify either --input, or --boundary-box, or "
        b"--coordinates.\n",
    )


def test_render() -> None:
    """Test `render` command."""
    run(
        COMMAND_LINES["render"] + ["--cache", "tests/data"],
        LOG + b"INFO Writing output SVG to out/map.svg...\n",
    )
    with (OUTPUT_PATH / "map.svg").open(encoding="utf-8") as output_file:
        root: Element = ElementTree.parse(output_file).getroot()

    # 8 expected elements: `defs`, `rect` (background), `g` (outline),
    # `g` (icon), 4 `text` elements (credits).
    assert len(root) == 8
    assert len(root[3][0]) == 0
    assert root.get("width") == "186.0"
    assert root.get("height") == "198.0"


def test_render_with_tooltips() -> None:
    """Test `render` command."""
    run(
        COMMAND_LINES["render_with_tooltips"] + ["--cache", "tests/data"],
        LOG + b"INFO Writing output SVG to out/map.svg...\n",
    )
    with (OUTPUT_PATH / "map.svg").open(encoding="utf-8") as output_file:
        root: Element = ElementTree.parse(output_file).getroot()

    # 8 expected elements: `defs`, `rect` (background), `g` (outline),
    # `g` (icon), 4 `text` elements (credits).
    assert len(root) == 8
    assert len(root[3][0]) == 1
    assert root[3][0][0].text == "natural: tree"
    assert root.get("width") == "186.0"
    assert root.get("height") == "198.0"


def test_icons() -> None:
    """Test `icons` command."""
    run(
        COMMAND_LINES["icons"],
        b"INFO Icons are written to out/icons_by_name and out/icons_by_id.\n"
        b"INFO Icon grid is written to out/icon_grid.svg.\n"
        b"INFO Icon grid is written to doc/grid.svg.\n",
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
        b"INFO MapCSS 0.2 scheme is written to out/map_machine_mapcss.\n",
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
        LOG + b"INFO Map is drawn to out/element.svg.\n",
    )
    assert (OUTPUT_PATH / "element.svg").is_file()


def test_unwrapped_draw() -> None:
    """Test `element` command from inside the project."""
    arguments: argparse.Namespace = parse_arguments(
        ["map_machine"] + COMMAND_LINES["draw"]
    )
    from map_machine.element.element import draw_element

    draw_element(arguments)


def test_tile() -> None:
    """Test `tile` command."""
    run(
        COMMAND_LINES["tile"] + ["--cache", "tests/data"],
        LOG + b"INFO Tile is drawn to out/tiles/tile_18_160199_88904.svg.\n"
        b"INFO SVG file is rasterized to out/tiles/tile_18_160199_88904.png.\n",
    )

    assert (OUTPUT_PATH / "tiles" / "tile_18_160199_88904.svg").is_file()
    assert (OUTPUT_PATH / "tiles" / "tile_18_160199_88904.png").is_file()
