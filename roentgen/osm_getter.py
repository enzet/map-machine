"""
Getting OpenStreetMap data from the web.
"""
import re
import time
import urllib
from pathlib import Path
from typing import Dict, Optional

import urllib3

from roentgen.ui import error

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


def get_osm(boundary_box: str, to_update: bool = False) -> Optional[str]:
    """
    Download OSM data from the web or get if from the cache.

    :param boundary_box: borders of the map part to download
    :param to_update: update cache files
    """
    result_file_name: Path = "map" / Path(boundary_box + ".osm")

    if not to_update and result_file_name.is_file():
        return result_file_name.open().read()

    matcher = re.match(
        "(?P<left>[0-9.-]*),(?P<bottom>[0-9.-]*)," +
        "(?P<right>[0-9.-]*),(?P<top>[0-9.-]*)",
        boundary_box)

    if not matcher:
        error("invalid boundary box")
        return None

    try:
        left = float(matcher.group("left"))
        bottom = float(matcher.group("bottom"))
        right = float(matcher.group("right"))
        top = float(matcher.group("top"))
    except ValueError:
        error("parsing boundary box")
        return None

    if left >= right:
        error("negative horizontal boundary")
        return None
    if bottom >= top:
        error("negative vertical boundary")
        return None
    if right - left > 0.5 or top - bottom > 0.5:
        error("box too big")
        return None

    content = get_data(
        "api.openstreetmap.org/api/0.6/map",
        {"bbox": boundary_box}, is_secure=True)

    result_file_name.open("w+").write(content.decode("utf-8"))

    return content.decode("utf-8")


def get_data(
        address: str, parameters: Dict[str, str], is_secure: bool = False) \
        -> bytes:
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
    result = pool_manager.request("GET", url)
    pool_manager.clear()
    time.sleep(2)
    return result.data
