import copy
import re

from typing import Any, Dict


STANDARD_COLOR: str = "444444"


def get_color(color: str, scheme: Dict[str, Any]):
    if color in scheme["colors"]:  # type: str
        return scheme["colors"][color]
    else:
        m = re.match("^#?(?P<color1>[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f])" +
            "(?P<color2>[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f])?$", color)
        if m:
            if "color2" in m.groups():
                return m.group("color1") + m.group("color2")
            else:
                return "".join(map(lambda x: x + x, m.group("color1")))
    return STANDARD_COLOR


def get_icon(
        tags: Dict[str, Any], scheme: Dict[str, Any],
        fill: str = STANDARD_COLOR):

    tags_hash = ",".join(tags.keys()) + ":" + \
        ",".join(map(lambda x: str(x), tags.values()))
    if tags_hash in scheme["cache"]:
        return scheme["cache"][tags_hash]
    main_icon = None
    extra_icons = []
    processed = set()
    for matcher in scheme["tags"]:
        matched = True
        for key in matcher["tags"]:
            if key not in tags:
                matched = False
                break
            if matcher["tags"][key] != "*" and \
                    matcher["tags"][key] != tags[key]:
                matched = False
                break
        if "no_tags" in matcher:
            for no_tag in matcher["no_tags"]:
                if no_tag in tags.keys():
                    matched = False
                    break
        if matched:
            if "draw" in matcher and not matcher["draw"]:
                processed |= set(matcher["tags"].keys())
            if "icon" in matcher:
                main_icon = copy.deepcopy(matcher["icon"])
                processed |= set(matcher["tags"].keys())
            if "over_icon" in matcher:
                if main_icon:  # TODO: check main icon in under icons
                    main_icon += matcher["over_icon"]
                    for key in matcher["tags"].keys():
                        processed.add(key)
            if "add_icon" in matcher:
                extra_icons += matcher["add_icon"]
                for key in matcher["tags"].keys():
                    processed.add(key)
            if "color" in matcher:
                fill = scheme["colors"][matcher["color"]]
                for key in matcher["tags"].keys():
                    processed.add(key)

    for color_name in ["color", "colour", "building:colour"]:
        if color_name in tags:
            fill = get_color(tags[color_name], scheme)
            if fill != STANDARD_COLOR:
                processed.add(color_name)
            else:
                print(f"No color {tags[color_name]}.")

    if main_icon:
        returned = [main_icon] + extra_icons, fill, processed
    else:
        returned = extra_icons, fill, processed

    scheme["cache"][tags_hash] = returned

    return returned

