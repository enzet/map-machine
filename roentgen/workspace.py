"""
File and directory path in the project.
"""
from pathlib import Path

# Project directories and files, that are the part of the repository.

SCHEME_PATH: Path = Path("scheme")
DEFAULT_SCHEME_PATH: Path = SCHEME_PATH / "default.yml"
ICONS_PATH: Path = Path("icons/icons.svg")
ICONS_CONFIG_PATH: Path = Path("icons/config.json")
GITHUB_TEST_PATH: Path = Path(".github/workflows/test.yml")
DATA_PATH: Path = Path("data")
MAPCSS_PART_FILE_PATH: Path = DATA_PATH / "roentgen_icons_part.mapcss"

# Generated directories and files.

_OUTPUT_PATH: Path = Path("out")
_ICONS_BY_ID_PATH: Path = _OUTPUT_PATH / "icons_by_id"
_ICONS_BY_NAME_PATH: Path = _OUTPUT_PATH / "icons_by_name"
_MAPCSS_PATH: Path = _OUTPUT_PATH / "roentgen_icons_mapcss"
_TILE_PATH: Path = _OUTPUT_PATH / "tiles"

MAPCSS_ICONS_DIRECTORY_NAME: str = "icons"


def check_and_create(directory: Path) -> Path:
    """Create directory if it doesn't exist and return it."""
    if not directory.is_dir():
        directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_output_path() -> Path:
    """Path for generated files."""
    return check_and_create(_OUTPUT_PATH)


def get_icons_by_id_path() -> Path:
    """Directory for the icon files named by identifiers."""
    return check_and_create(_ICONS_BY_ID_PATH)


def get_icons_by_name_path() -> Path:
    """Directory for the icon files named by human-readable names."""
    return check_and_create(_ICONS_BY_NAME_PATH)


def get_tile_path() -> Path:
    """Directory for tiles."""
    return check_and_create(_TILE_PATH)


def get_mapcss_path() -> Path:
    """Directory for MapCSS files."""
    return check_and_create(_MAPCSS_PATH)


def get_mapcss_file_path() -> Path:
    """Directory for MapCSS files."""
    return get_mapcss_path() / "roentgen_icons.mapcss"


def get_mapcss_icons_path() -> Path:
    """Directory for icons used by MapCSS file."""
    return check_and_create(get_mapcss_path() / MAPCSS_ICONS_DIRECTORY_NAME)


def get_icon_grid_path() -> Path:
    """Icon grid path."""
    return get_output_path() / "icon_grid.svg"


def get_taginfo_file_path() -> Path:
    """Path to file with project information for Taginfo."""
    return get_output_path() / "roentgen_taginfo.json"
