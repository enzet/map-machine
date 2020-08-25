import os
import re
import time
import urllib
import urllib3

from typing import Dict, Optional

from roentgen.ui import error


def get_osm(boundary_box: str, to_update: bool = False) -> Optional[str]:
    """
    Download OSM data from the web or get if from the cache.

    :param boundary_box: borders of the map part to download
    :param to_update: update cache files
    """
    result_file_name = os.path.join("map", boundary_box + ".osm")

    if not to_update and os.path.isfile(result_file_name):
        return open(result_file_name).read()

    matcher = re.match("(?P<left>[0-9.-]*),(?P<bottom>[0-9.-]*)," +
        "(?P<right>[0-9.-]*),(?P<top>[0-9.-]*)", boundary_box)

    if not matcher:
        error("invalid boundary box")
        return

    try:
        left = float(matcher.group("left"))
        bottom = float(matcher.group("bottom"))
        right = float(matcher.group("right"))
        top = float(matcher.group("top"))
    except ValueError:
        error("parsing boundary box")
        return

    if left >= right:
        error("negative horizontal boundary")
        return
    if bottom >= top:
        error("negative vertical boundary")
        return
    if right - left > 0.5 or top - bottom > 0.5:
        error("box too big")
        return

    content = get_data("api.openstreetmap.org/api/0.6/map",
            {"bbox": boundary_box}, is_secure=True)

    open(result_file_name, "w+").write(content.decode("utf-8"))

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
