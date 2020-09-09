"""
OSM address tag processing.

Author: Sergey Vartanov (me@enzet.ru).
"""
from typing import List, Any, Dict


def get_address(tags: Dict[str, Any], draw_captions_mode: str):

    address: List[str] = []

    if draw_captions_mode != "main":
        if "addr:postcode" in tags:
            address.append(tags["addr:postcode"])
            tags.pop("addr:postcode", None)
        if "addr:country" in tags:
            address.append(tags["addr:country"])
            tags.pop("addr:country", None)
        if "addr:city" in tags:
            address.append(tags["addr:city"])
            tags.pop("addr:city", None)
        if "addr:street" in tags:
            street = tags["addr:street"]
            if street.startswith("улица "):
                street = "ул. " + street[len("улица "):]
            address.append(street)
            tags.pop("addr:street", None)

    if "addr:housenumber" in tags:
        address.append(tags["addr:housenumber"])
        tags.pop("addr:housenumber", None)

