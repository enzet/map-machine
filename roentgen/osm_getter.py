import os
import re

from typing import Optional

from roentgen.ui import error
from roentgen import network


def get_osm(boundary_box: str, to_update: bool = False) -> Optional[str]:
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

    content = network.get_data("api.openstreetmap.org/api/0.6/map",
            {"bbox": boundary_box}, is_secure=True)

    open(result_file_name, "w+").write(content.decode("utf-8"))

    return content.decode("utf-8")
