"""
Utility for network connections.

Author: Sergey Vartanov (me@enzet.ru)
"""
import json
import os
import urllib
import urllib3
import time

from datetime import datetime, timedelta
from typing import Dict, List


def get_data(address: str, parameters: Dict[str, str], is_secure: bool=False, name: str=None) -> bytes:
    """
    Construct Internet page URL and get its descriptor.

    :param address: first part of URL without "http://"
    :param parameters: URL parameters
    :param is_secure: https or http
    :param name: name to display in logs
    :return: connection descriptor
    """
    url = "http" + ("s" if is_secure else "") + "://" + address
    if len(parameters) > 0:
        url += "?" + urllib.parse.urlencode(parameters)
    if not name:
        name = url
    print("getting " + name)
    pool_manager = urllib3.PoolManager()
    url = url.replace(" ", "_")
    urllib3.disable_warnings()
    result = pool_manager.request("GET", url)
    pool_manager.clear()
    time.sleep(2)
    return result.data
