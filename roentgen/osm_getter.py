"""
Getting OpenStreetMap data from the web.
"""
import logging
import time
import urllib
from dataclasses import dataclass
from pathlib import Path

import urllib3

from roentgen.boundary_box import BoundaryBox

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
        with cache_file_path.open() as output_file:
            return output_file.read()

    content: str = get_data(
        "api.openstreetmap.org/api/0.6/map",
        {"bbox": boundary_box.get_format()},
        is_secure=True,
    ).decode("utf-8")

    with cache_file_path.open("w+") as output_file:
        output_file.write(content)

    return content


def get_data(
    address: str, parameters: dict[str, str], is_secure: bool = False
) -> bytes:
    """
    Construct Internet page URL and get its descriptor.

    :param address: first part of URL without "http://"
    :param parameters: URL parameters
    :param is_secure: https or http
    :return: connection descriptor
    """
    url: str = f"http{('s' if is_secure else '')}://{address}"
    if len(parameters) > 0:
        url += f"?{urllib.parse.urlencode(parameters)}"
    logging.info(f"Getting {url}...")
    pool_manager: urllib3.PoolManager = urllib3.PoolManager()
    urllib3.disable_warnings()

    try:
        result = pool_manager.request("GET", url)
    except urllib3.exceptions.MaxRetryError:
        raise NetworkError("Cannot download data: too many attempts.")

    pool_manager.clear()
    time.sleep(SLEEP_TIME_BETWEEN_REQUESTS)
    return result.data
