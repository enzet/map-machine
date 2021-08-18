"""
File and directory path in the project.
"""
from pathlib import Path

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def check_and_create(directory: Path) -> Path:
    """Create directory if it doesn't exist and return it."""
    if not directory.is_dir():
        directory.mkdir(parents=True, exist_ok=True)
    return directory


class Workspace:
    """
    Project file and directory paths and generated files and directories.
    """

    # Project directories and files, that are the part of the repository.

    SCHEME_PATH: Path = Path("scheme")
    DEFAULT_SCHEME_PATH: Path = SCHEME_PATH / "default.yml"
    ICONS_PATH: Path = Path("icons/icons.svg")
    ICONS_CONFIG_PATH: Path = Path("icons/config.json")
    GITHUB_TEST_PATH: Path = Path(".github/workflows/test.yml")
    DATA_PATH: Path = Path("data")

    # Generated directories and files.

    MAPCSS_ICONS_DIRECTORY_NAME: str = "icons"

    def __init__(self, output_path: Path) -> None:
        self.output_path: Path = output_path
        check_and_create(output_path)

        self._icons_by_id_path: Path = output_path / "icons_by_id"
        self._icons_by_name_path: Path = output_path / "icons_by_name"
        self._mapcss_path: Path = output_path / "roentgen_mapcss"
        self._tile_path: Path = output_path / "tiles"

    def get_icons_by_id_path(self) -> Path:
        """Directory for the icon files named by identifiers."""
        return check_and_create(self._icons_by_id_path)

    def get_icons_by_name_path(self) -> Path:
        """Directory for the icon files named by human-readable names."""
        return check_and_create(self._icons_by_name_path)

    def get_tile_path(self) -> Path:
        """Directory for tiles."""
        return check_and_create(self._tile_path)

    def get_mapcss_path(self) -> Path:
        """Directory for MapCSS files."""
        return check_and_create(self._mapcss_path)

    def get_mapcss_file_path(self) -> Path:
        """Directory for MapCSS files."""
        return self.get_mapcss_path() / "roentgen.mapcss"

    def get_mapcss_icons_path(self) -> Path:
        """Directory for icons used by MapCSS file."""
        return check_and_create(
            self.get_mapcss_path() / self.MAPCSS_ICONS_DIRECTORY_NAME
        )

    def get_icon_grid_path(self) -> Path:
        """Icon grid path."""
        return self.output_path / "icon_grid.svg"

    def get_taginfo_file_path(self) -> Path:
        """Path to file with project information for Taginfo."""
        return self.output_path / "roentgen_taginfo.json"


workspace = Workspace(Path("out"))
