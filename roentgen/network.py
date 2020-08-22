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
        url += "?" + "&".join(parameters)  # urllib.parse.urlencode(parameters)
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


def get_content(address, parameters, cache_file_name, kind, is_secure, name=None, exceptions=None, update_cache=False):
    """
    Read content from URL or from cached file.

    :param address: first part of URL without "http://"
    :param parameters: URL parameters
    :param cache_file_name: name of cache file
    :param kind: type of content: "html" or "json"
    :return: content if exist
    """
    if exceptions and address in exceptions:
        return None
    if os.path.isfile(cache_file_name) and \
            datetime(1, 1, 1).fromtimestamp(os.stat(cache_file_name).st_mtime) > \
                datetime.now() - timedelta(days=90) and \
            not update_cache:
        with open(cache_file_name) as cache_file:
            if kind == "json":
                try:
                    return json.load(cache_file)
                except ValueError:
                    return None
            if kind == "html":
                return cache_file.read()
    else:
        try:
            data = get_data(address, parameters, is_secure=is_secure, name=name)
            if kind == "json":
                try:
                    obj = json.loads(data)
                    with open(cache_file_name, "w+") as cached:
                        cached.write(json.dumps(obj, indent=4))
                    return obj
                except ValueError:
                    print("cannot get " + address + " " + str(parameters))
                    return None
            if kind == "html":
                with open(cache_file_name, "w+") as cached:
                    cached.write(data)
                return data
        except Exception as e:
            print("during getting JSON from " + address + " with parameters " + str(parameters))
            print(e)
            if exceptions:
                exceptions.append(address)
            return None
