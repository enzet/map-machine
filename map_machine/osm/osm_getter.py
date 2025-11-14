"""Getting OpenStreetMap data from the web."""
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import urllib3

from map_machine.geometry.boundary_box import BoundaryBox

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

SLEEP_TIME_BETWEEN_REQUESTS: float = 2.0


@dataclass
class NetworkError(Exception):
    """Failed network request."""

    message: str


def get_osm(
    boundary_box: BoundaryBox, cache_file_path: Path, to_update: bool = False
) -> str:
    """
    Download OSM data from the web or get if from the cache.

    :param boundary_box: borders of the map part to download
    :param cache_file_path: cache file to store downloaded OSM data
    :param to_update: update cache files
    """
    if not to_update and cache_file_path.is_file():
        with cache_file_path.open(encoding="utf-8") as output_file:
            return output_file.read()

    content: bytes = get_data(
        "https://api.openstreetmap.org/api/0.6/map",
        {"bbox": boundary_box.get_format()},
    )

    if not content.startswith(b"<"):
        if content == (
            b"You requested too many nodes (limit is 50000). Either request a "
            b"smaller area, or use planet.osm"
        ):
            raise NetworkError(
                "Cannot download data: too many nodes (limit is 50000). Try "
                "to request smaller area."
            )

        raise NetworkError("Cannot download data.")

    with cache_file_path.open("bw+") as output_file:
        output_file.write(content)

    return content.decode("utf-8")


def get_data(address: str, parameters: dict[str, str]) -> bytes:
    """
    Construct Internet page URL and get its descriptor.

    :param address: URL without parameters
    :param parameters: URL parameters
    :return: connection descriptor
    """
    logging.info(f"Getting {address}...")
    pool_manager: urllib3.PoolManager = urllib3.PoolManager()
    urllib3.disable_warnings()

    try:
        result = pool_manager.request("GET", address, fields=parameters)
    except urllib3.exceptions.MaxRetryError:
        raise NetworkError("Cannot download data: too many attempts.")

    pool_manager.clear()
    time.sleep(SLEEP_TIME_BETWEEN_REQUESTS)
    return result.data
