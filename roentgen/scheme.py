"""
Röntgen drawing scheme.

Author: Sergey Vartanov (me@enzet.ru).
"""
import copy
import yaml

from colour import Color
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from roentgen.extract_icon import DEFAULT_SHAPE_ID

DEFAULT_COLOR: Color = Color("#444444")


@dataclass
class IconSet:
    """
    Node representation: icons and color.
    """
    icons: List[List[str]]  # list of lists of shape identifiers
    color: Color  # fill color of all icons
    # tag keys that were processed to create icon set (other
    # tag keys should be displayed by text or ignored)
    processed: Set[str]
    is_default: bool


class Scheme:
    """
    Map style.

    Specifies map colors and rules to draw icons for OpenStreetMap tags.
    """
    def __init__(self, file_name: str):
        """
        :param file_name: scheme file name with tags, colors, and tag key
            specification
        """
        with open(file_name) as input_file:
            content: Dict[str, Any] = yaml.load(
                input_file.read(), Loader=yaml.FullLoader)

        self.nodes: List[Dict[str, Any]] = content["nodes"]
        self.ways: List[Dict[str, Any]] = content["ways"]

        self.colors: Dict[str, str] = content["colors"]

        self.tags_to_write: List[str] = content["tags_to_write"]
        self.prefix_to_write: List[str] = content["prefix_to_write"]
        self.tags_to_skip: List[str] = content["tags_to_skip"]
        self.prefix_to_skip: List[str] = content["prefix_to_skip"]

        # Storage for created icon sets.
        self.cache: Dict[str, IconSet] = {}

    def get_color(self, color: str) -> Color:
        """
        Return color if the color is in scheme, otherwise return default color.

        :return: 6-digit color specification with "#"
        """
        if color in self.colors:
            return Color("#" + self.colors[color])
        if color.lower() in self.colors:
            return Color("#" + self.colors[color.lower()])
        try:
            return Color(color)
        except ValueError:
            pass

        return DEFAULT_COLOR

    def is_no_drawable(self, key: str) -> bool:
        """
        Return true if key is specified as no drawable (should not be
        represented on the map as icon set or as text) by the scheme.

        :param key: OpenStreetMap tag key
        """
        if key in self.tags_to_write or key in self.tags_to_skip:
            return True
        for prefix in self.prefix_to_write + self.prefix_to_skip:  # type: str
            if key[:len(prefix) + 1] == prefix + ":":
                return True
        return False

    def is_writable(self, key: str) -> bool:
        """
        Return true if key is specified as writable (should be represented on
        the map as text) by the scheme.

        :param key: OpenStreetMap tag key
        """
        if key in self.tags_to_skip:
            return False
        if key in self.tags_to_write:
            return True
        for prefix in self.prefix_to_write:
            if key[:len(prefix) + 1] == prefix + ":":
                return True
        return False

    def get_icon(self, tags: Dict[str, Any]) -> IconSet:
        """
        Construct icon set.

        :param tags: OpenStreetMap element tags dictionary
        """
        tags_hash: str = \
            ",".join(tags.keys()) + ":" + \
            ",".join(map(lambda x: str(x), tags.values()))

        if tags_hash in self.cache:
            return self.cache[tags_hash]

        main_icon: Optional[List[str]] = None
        extra_icons: List[List[str]] = []
        processed: Set[str] = set()
        fill: Color = DEFAULT_COLOR

        for matcher in self.nodes:  # type: Dict[str, Any]
            matched: bool = True
            for key in matcher["tags"]:  # type: str
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
                    extra_icons += [matcher["add_icon"]]
                    for key in matcher["tags"].keys():
                        processed.add(key)
                if "color" in matcher:
                    fill = self.get_color(matcher["color"])
                    for key in matcher["tags"].keys():
                        processed.add(key)

        for tag_key in tags:  # type: str
            if tag_key in ["color", "colour"] or tag_key.endswith(":color") or \
                    tag_key.endswith(":colour"):
                fill = self.get_color(tags[tag_key])
                processed.add(tag_key)

        if main_icon:
            result_set: List[List[str]] = [main_icon] + extra_icons
        else:
            result_set: List[List[str]] = extra_icons

        keys_left = list(filter(
            lambda x: x not in processed and
            not self.is_no_drawable(x), tags.keys()))

        is_default: bool = False
        if not result_set and keys_left:
            result_set = [[DEFAULT_SHAPE_ID]]
            is_default = True

        returned: IconSet = IconSet(result_set, fill, processed, is_default)

        self.cache[tags_hash] = returned

        return returned
