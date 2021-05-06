"""
Röntgen drawing scheme.

Author: Sergey Vartanov (me@enzet.ru).
"""
import copy
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import yaml
from colour import Color

from roentgen.icon import DEFAULT_SHAPE_ID, Shape, IconExtractor
from roentgen.text import Label, get_address, get_text

DEFAULT_COLOR: Color = Color("#444444")


@dataclass
class Icon:
    """
    Node representation: icons and color.
    """
    main_icon: List[Shape]  # list of icons
    extra_icons: List[List[Shape]]  # list of lists of icons
    color: Color  # fill color of all icons
    # tag keys that were processed to create icon set (other
    # tag keys should be displayed by text or ignored)
    processed: Set[str]
    is_default: bool


@dataclass
class LineStyle:
    style: Dict[str, Union[int, float, str]]
    priority: float = 0.0


class MatchingType(Enum):
    NOT_MATCHED = 0
    MATCHED_BY_SET = 1
    MATCHED_BY_WILDCARD = 2
    MATCHED = 3


def is_matched_tag(
    matcher_tag_key: str, matcher_tag_value: Union[str, list],
    tags: Dict[str, str]
) -> MatchingType:
    """
    Check whether element tags contradict tag matcher.

    :param matcher_tag_key: tag key
    :param matcher_tag_value: tag value, tag value list, or "*"
    :param tags: element tags to check
    """
    if matcher_tag_key in tags:
        if matcher_tag_value == "*":
            return MatchingType.MATCHED_BY_WILDCARD
        if (
            isinstance(matcher_tag_value, str) and
            tags[matcher_tag_key] == matcher_tag_value
        ):
            return MatchingType.MATCHED
        if (
            isinstance(matcher_tag_value, list) and
            tags[matcher_tag_key] in matcher_tag_value
        ):
            return MatchingType.MATCHED_BY_SET
    return MatchingType.NOT_MATCHED


def is_matched(matcher: Dict[str, Any], tags: Dict[str, str]) -> bool:
    """
    Check whether element tags matches tag matcher.

    :param matcher: dictionary with tag keys and values, value lists, or "*"
    :param tags: element tags to match
    """
    matched: bool = True

    for config_tag_key in matcher["tags"]:
        config_tag_key: str
        tag_matcher = matcher["tags"][config_tag_key]
        if (
            is_matched_tag(config_tag_key, tag_matcher, tags) ==
                MatchingType.NOT_MATCHED
        ):
            matched = False
            break

    if "no_tags" in matcher:
        for config_tag_key in matcher["no_tags"]:
            config_tag_key: str
            tag_matcher = matcher["no_tags"][config_tag_key]
            if (
                is_matched_tag(config_tag_key, tag_matcher, tags) !=
                    MatchingType.NOT_MATCHED
            ):
                matched = False
                break

    return matched


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

        self.icons: List[Dict[str, Any]] = content["node_icons"]
        self.ways: List[Dict[str, Any]] = content["ways"]

        self.colors: Dict[str, str] = content["colors"]

        self.area_tags: List[Dict[str, str]] = content["area_tags"]

        self.tags_to_write: List[str] = content["tags_to_write"]
        self.prefix_to_write: List[str] = content["prefix_to_write"]
        self.tags_to_skip: List[str] = content["tags_to_skip"]
        self.prefix_to_skip: List[str] = content["prefix_to_skip"]

        # Storage for created icon sets.
        self.cache: Dict[str, Tuple[Icon, int]] = {}

    def get_color(self, color: str) -> Color:
        """
        Return color if the color is in scheme, otherwise return default color.

        :param color: input color string representation
        :return: 6-digit color specification with "#"
        """
        if color in self.colors:
            return Color(self.colors[color])
        if color.lower() in self.colors:
            return Color(self.colors[color.lower()])
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
            if key[:len(prefix) + 1] == f"{prefix}:":
                return True
        return False

    def is_writable(self, key: str) -> bool:
        """
        Return true if key is specified as writable (should be represented on
        the map as text) by the scheme.

        :param key: OpenStreetMap tag key
        """
        if key in self.tags_to_skip:  # type: str
            return False
        if key in self.tags_to_write:  # type: str
            return True
        for prefix in self.prefix_to_write:  # type: str
            if key[:len(prefix) + 1] == f"{prefix}:":
                return True
        return False

    def get_icon(
        self, icon_extractor: IconExtractor, tags: Dict[str, Any],
        for_: str = "node"
    ) -> Tuple[Icon, int]:
        """
        Construct icon set.

        :param icon_extractor: extractor with icon specifications
        :param tags: OpenStreetMap element tags dictionary
        :param for_: target (node, way, area or relation)
        """
        tags_hash: str = (
            ",".join(tags.keys()) + ":" + ",".join(map(str, tags.values()))
        )
        if tags_hash in self.cache:
            return self.cache[tags_hash]

        main_icon_id: Optional[List[str]] = None
        extra_icon_ids: List[List[str]] = []
        processed: Set[str] = set()
        fill: Color = DEFAULT_COLOR
        priority: int = 0

        for index, matcher in enumerate(self.icons):
            # type: (int, Dict[str, Any])
            matched: bool = is_matched(matcher, tags)
            if not matched:
                continue
            priority = len(self.icons) - index
            if "draw" in matcher and not matcher["draw"]:
                processed |= set(matcher["tags"].keys())
            if "icon" in matcher:
                main_icon_id = copy.deepcopy(matcher["icon"])
                processed |= set(matcher["tags"].keys())
            if "over_icon" in matcher:
                if main_icon_id:  # TODO: check main icon in under icons
                    main_icon_id += matcher["over_icon"]
                    for key in matcher["tags"].keys():
                        processed.add(key)
            if "add_icon" in matcher:
                extra_icon_ids += [matcher["add_icon"]]
                for key in matcher["tags"].keys():
                    processed.add(key)
            if "color" in matcher:
                fill = self.get_color(matcher["color"])
                for key in matcher["tags"].keys():
                    processed.add(key)

        for tag_key in tags:  # type: str
            if (tag_key.endswith(":color") or
                    tag_key.endswith(":colour")):
                fill = self.get_color(tags[tag_key])
                processed.add(tag_key)

        for tag_key in tags:  # type: str
            if tag_key in ["color", "colour"]:
                fill = self.get_color(tags[tag_key])
                processed.add(tag_key)

        keys_left = list(filter(
            lambda x: x not in processed and
            not self.is_no_drawable(x), tags.keys()
        ))

        is_default: bool = False
        if not main_icon_id and not extra_icon_ids and keys_left:
            main_icon_id = [DEFAULT_SHAPE_ID]
            is_default = True

        main_icon: List[Shape] = []
        if main_icon_id:
            main_icon = list(map(
                lambda x: icon_extractor.get_path(x)[0], main_icon_id
            ))

        extra_icons: List[List[Shape]] = []
        for icon_id in extra_icon_ids:
            extra_icons.append(list(map(
                lambda x: icon_extractor.get_path(x)[0], icon_id)))

        returned: Icon = Icon(
            main_icon, extra_icons, fill, processed, is_default
        )
        self.cache[tags_hash] = returned, priority

        return returned, priority

    def get_style(self, tags: Dict[str, Any], scale):

        line_styles = []

        for element in self.ways:  # type: Dict[str, Any]
            priority = 0
            matched: bool = is_matched(element, tags)
            if not matched:
                continue
            style: Dict[str, Any] = {"fill": "none"}
            if "priority" in element:
                priority = element["priority"]
            for key in element:  # type: str
                if key not in [
                        "tags", "no_tags", "priority", "level", "icon",
                        "r", "r1", "r2"]:
                    value = element[key]
                    if isinstance(value, str) and value.endswith("_color"):
                        value = self.get_color(value)
                    style[key] = value
            if "r" in element:
                style["stroke-width"] = (element["r"] * scale)
            if "r1" in element:
                style["stroke-width"] = (element["r1"] * scale + 1)
            if "r2" in element:
                style["stroke-width"] = (element["r2"] * scale + 2)

            line_styles.append(LineStyle(style, priority))

        return line_styles

    def construct_text(self, tags, draw_captions) -> List[Label]:
        """
        Construct labels for not processed tags.
        """
        texts: List[Label] = []

        name = None
        alt_name = None
        if "name" in tags:
            name = tags["name"]
            tags.pop("name", None)
        if "name:ru" in tags:
            if not name:
                name = tags["name:ru"]
                tags.pop("name:ru", None)
            tags.pop("name:ru", None)
        if "name:en" in tags:
            if not name:
                name = tags["name:en"]
                tags.pop("name:en", None)
            tags.pop("name:en", None)
        if "alt_name" in tags:
            if alt_name:
                alt_name += ", "
            else:
                alt_name = ""
            alt_name += tags["alt_name"]
            tags.pop("alt_name")
        if "old_name" in tags:
            if alt_name:
                alt_name += ", "
            else:
                alt_name = ""
            alt_name += "ex " + tags["old_name"]

        address: List[str] = get_address(tags, draw_captions)

        if name:
            texts.append(Label(name, Color("black")))
        if alt_name:
            texts.append(Label(f"({alt_name})"))
        if address:
            texts.append(Label(", ".join(address)))

        if draw_captions == "main":
            return texts

        for text in get_text(tags):  # type: str
            if text:
                texts.append(Label(text))

        if "route_ref" in tags:
            texts.append(Label(tags["route_ref"].replace(";", " ")))
            tags.pop("route_ref", None)
        if "cladr:code" in tags:
            texts.append(Label(tags["cladr:code"], size=7))
            tags.pop("cladr:code", None)
        if "website" in tags:
            link = tags["website"]
            if link[:7] == "http://":
                link = link[7:]
            if link[:8] == "https://":
                link = link[8:]
            if link[:4] == "www.":
                link = link[4:]
            if link[-1] == "/":
                link = link[:-1]
            link = link[:25] + ("..." if len(tags["website"]) > 25 else "")
            texts.append(Label(link, Color("#000088")))
            tags.pop("website", None)
        for k in ["phone"]:
            if k in tags:
                texts.append(Label(tags[k], Color("#444444")))
                tags.pop(k)
        for tag in tags:
            if self.is_writable(tag):
                texts.append(Label(tags[tag]))
        return texts

    def is_area(self, tags: Dict[str, str]) -> bool:
        for matcher in self.area_tags:
            if is_matched(matcher, tags):
                return True
        return False
