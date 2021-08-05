"""
Getting OpenStreetMap data from the web.
"""
import time
import urllib
from pathlib import Path
from typing import Dict, Optional

import logging
import urllib3

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

from roentgen.ui import BoundaryBox


def get_osm(
    boundary_box: str, cache_path: Path, to_update: bool = False
) -> Optional[str]:
    """
    Download OSM data from the web or get if from the cache.

    :param boundary_box: borders of the map part to download
    :param cache_path: cache directory to store downloaded OSM files
    :param to_update: update cache files
    """
    result_file_name: Path = cache_path / f"{boundary_box}.osm"

    if not to_update and result_file_name.is_file():
        return result_file_name.open().read()

    content: Optional[bytes] = get_data(
        "api.openstreetmap.org/api/0.6/map",
        {"bbox": boundary_box},
        is_secure=True,
    )
    if content is None:
        return None
    if BoundaryBox.from_text(boundary_box) is None:
        return None

    result_file_name.open("w+").write(content.decode("utf-8"))

    return content.decode("utf-8")


def get_data(
    address: str, parameters: Dict[str, str], is_secure: bool = False
) -> Optional[bytes]:
    """
    Construct Internet page URL and get its descriptor.

    :param address: first part of URL without "http://"
    :param parameters: URL parameters
    :param is_secure: https or http
    :return: connection descriptor
    """
    url = "http" + ("s" if is_secure else "") + "://" + address
    if len(parameters) > 0:
        url += "?" + urllib.parse.urlencode(parameters)
    print("Getting " + url + "...")
    pool_manager = urllib3.PoolManager()
    urllib3.disable_warnings()

    try:
        result = pool_manager.request("GET", url)
    except urllib3.exceptions.MaxRetryError:
        logging.fatal("Too many attempts.")
        return None

    pool_manager.clear()
    time.sleep(2)
    return result.data
