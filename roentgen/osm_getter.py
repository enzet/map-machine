"""
Getting OpenStreetMap data from the web.
"""
import time
import urllib
from pathlib import Path
from typing import Dict, Optional

import logging
import urllib3

from roentgen.ui import BoundaryBox

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


class NetworkError(Exception):
    def __init__(self, message: str):
        super().__init__()
        self.message: str = message


def get_osm(
    boundary_box: BoundaryBox, cache_path: Path, to_update: bool = False
) -> str:
    """
    Download OSM data from the web or get if from the cache.

    :param boundary_box: borders of the map part to download
    :param cache_path: cache directory to store downloaded OSM files
    :param to_update: update cache files
    """
    result_file_name: Path = cache_path / f"{boundary_box.get_format()}.osm"

    if not to_update and result_file_name.is_file():
        return result_file_name.open().read()

    content: Optional[bytes] = get_data(
        "api.openstreetmap.org/api/0.6/map",
        {"bbox": boundary_box.get_format()},
        is_secure=True,
    ).decode("utf-8")

    with result_file_name.open("w+") as output_file:
        output_file.write(content)

    return content


def get_data(
    address: str, parameters: Dict[str, str], is_secure: bool = False
) -> bytes:
    """
    Construct Internet page URL and get its descriptor.

    :param address: first part of URL without "http://"
    :param parameters: URL parameters
    :param is_secure: https or http
    :return: connection descriptor
    """
    url: str = "http" + ("s" if is_secure else "") + "://" + address
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
    time.sleep(2)
    return result.data
