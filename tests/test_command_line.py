"""
Test command line commands.
"""
from pathlib import Path
from subprocess import PIPE, Popen

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

from xml.etree import ElementTree
from xml.etree.ElementTree import Element


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


def test_wrong_render_arguments() -> None:
    """Test `render` command with wrong arguments."""
    error_run(
        ["render", "-z", "17"],
        b"CRITICAL Specify either --boundary-box, or --input.\n",
    )


def test_render() -> None:
    """Test `render` command."""
    run(
        [
            "render",
            "-b",
            "10.000,20.000,10.001,20.001",
            "--cache",
            "tests/data",
        ],
        b"INFO Writing output SVG to out/map.svg...\n",
    )
    with Path("out/map.svg").open() as output_file:
        root: Element = ElementTree.parse(output_file).getroot()

    assert len(root) == 4
    assert root.get("width") == "186.0"
    assert root.get("height") == "198.0"


def test_icons() -> None:
    """Test `icons` command."""
    run(
        ["icons"],
        b"INFO Icon grid is written to out/icon_grid.svg.\n"
        b"INFO Icons are written to out/icons_by_name and out/icons_by_id.\n",
    )


def test_mapcss() -> None:
    """Test `mapcss` command."""
    run(
        ["mapcss"],
        b"INFO MapCSS 0.2 scheme is written to out/map_machine_mapcss.\n",
    )


def test_element() -> None:
    """Test `element` command."""
    run(
        ["element", "--node", "amenity=bench,material=wood"],
        b"INFO Element is written to out/element.svg.\n",
    )


def test_tile() -> None:
    """Test `tile` command."""
    run(
        ["tile", "--coordinates", "50.000,40.000", "--cache", "tests/data"],
        b"INFO Tile is drawn to out/tiles/tile_18_160199_88904.svg.\n"
        b"INFO SVG file is rasterized to out/tiles/tile_18_160199_88904.png.\n",
    )
