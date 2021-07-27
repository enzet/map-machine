"""
Röntgen drawing scheme.
"""
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import yaml
from colour import Color

from roentgen.direction import DirectionSet
from roentgen.icon import (
    DEFAULT_COLOR, DEFAULT_SHAPE_ID, Icon, IconSet, ShapeExtractor,
    ShapeSpecification
)
from roentgen.text import Label, get_address, get_text

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"


@dataclass
class LineStyle:
    """
    SVG line style and its priority.
    """

    style: Dict[str, Union[int, float, str]]
    priority: float = 0.0


class MatchingType(Enum):
    """
    Description on how tag was matched.
    """

    NOT_MATCHED = 0
    MATCHED_BY_SET = 1
    MATCHED_BY_WILDCARD = 2
    MATCHED = 3


def is_matched_tag(
    matcher_tag_key: str,
    matcher_tag_value: Union[str, list],
    tags: Dict[str, str],
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
            isinstance(matcher_tag_value, str)
            and tags[matcher_tag_key] == matcher_tag_value
        ):
            return MatchingType.MATCHED
        if (
            isinstance(matcher_tag_value, list)
            and tags[matcher_tag_key] in matcher_tag_value
        ):
            return MatchingType.MATCHED_BY_SET
    return MatchingType.NOT_MATCHED


def get_selector(key: str, value: str, prefix: str = "") -> str:
    """Get MapCSS 0.2 selector for one key."""
    if prefix:
        key = f"{prefix}:{key}"
    if value == "*":
        return f"[{key}]"
    if '"' in value:
        return f"[{key}='{value}']"
    return f'[{key}="{value}"]'


class Matcher:
    """
    Tag matching.
    """

    def __init__(self, structure: Dict[str, Any]):
        self.tags: Dict[str, str] = structure["tags"]

        self.exception: Dict[str, str] = {}
        if "exception" in structure:
            self.exception = structure["exception"]

        self.replace_shapes: bool = True
        if "replace_shapes" in structure:
            self.replace_shapes = structure["replace_shapes"]

        self.location_restrictions: Dict[str, str] = {}
        if "location_restrictions" in structure:
            self.location_restrictions = structure["location_restrictions"]

    def is_matched(self, tags: Dict[str, str]) -> bool:
        """
        Check whether element tags matches tag matcher.

        :param tags: element tags to match
        """
        matched: bool = True

        for config_tag_key in self.tags:
            config_tag_key: str
            tag_matcher = self.tags[config_tag_key]
            if (
                is_matched_tag(config_tag_key, tag_matcher, tags)
                == MatchingType.NOT_MATCHED
            ):
                matched = False
                break

        if self.exception:
            for config_tag_key in self.exception:
                config_tag_key: str
                tag_matcher = self.exception[config_tag_key]
                if (
                    is_matched_tag(config_tag_key, tag_matcher, tags)
                    != MatchingType.NOT_MATCHED
                ):
                    matched = False
                    break

        return matched

    def get_mapcss_selector(self, prefix: str = "") -> str:
        """
        Construct MapCSS 0.2 selector from the node matcher.

        See https://wiki.openstreetmap.org/wiki/MapCSS/0.2
        """
        return "".join([get_selector(x, y, prefix) for (x, y) in self.tags.items()])


class NodeMatcher(Matcher):
    """
    Tag specification matcher.
    """

    def __init__(self, structure: Dict[str, Any]):
        # Dictionary with tag keys and values, value lists, or "*"
        super().__init__(structure)

        self.draw: bool = True
        if "draw" in structure:
            self.draw = structure["draw"]

        self.shapes = None
        if "shapes" in structure:
            self.shapes = structure["shapes"]

        self.over_icon = None
        if "over_icon" in structure:
            self.over_icon = structure["over_icon"]

        self.add_shapes = None
        if "add_shapes" in structure:
            self.add_shapes = structure["add_shapes"]

        self.set_main_color = None
        if "set_main_color" in structure:
            self.set_main_color = structure["set_main_color"]

        self.under_icon = None
        if "under_icon" in structure:
            self.under_icon = structure["under_icon"]

        self.with_icon = None
        if "with_icon" in structure:
            self.with_icon = structure["with_icon"]


class WayMatcher(Matcher):
    """
    Special tag matcher for ways.
    """

    def __init__(self, structure: Dict[str, Any], scheme: "Scheme"):
        super().__init__(structure)
        self.style: Dict[str, Any] = {"fill": "none"}
        if "style" in structure:
            style: Dict[str, Any] = structure["style"]
            for key in style:
                if str(style[key]).endswith("_color"):
                    self.style[key] = scheme.get_color(style[key]).hex.upper()
                else:
                    self.style[key] = style[key]
        self.priority = 0
        if "priority" in structure:
            self.priority = structure["priority"]


class RoadMatcher(Matcher):
    """
    Special tag matcher for highways.
    """

    def __init__(self, structure: Dict[str, Any], scheme: "Scheme"):
        super().__init__(structure)
        self.border_color: Color = Color(
            scheme.get_color(structure["border_color"])
        )
        self.color: Color = Color("white")
        if "color" in structure:
            self.color = Color(scheme.get_color(structure["color"]))
        self.default_width: float = structure["default_width"]
        self.priority: float = 0
        if "priority" in structure:
            self.priority = structure["priority"]


class Scheme:
    """
    Map style.

    Specifies map colors and rules to draw icons for OpenStreetMap tags.
    """

    def __init__(self, file_name: Path):
        """
        :param file_name: name of the scheme file with tags, colors, and tag key
            specification
        """
        with file_name.open() as input_file:
            content: Dict[str, Any] = yaml.load(
                input_file.read(), Loader=yaml.FullLoader
            )
        self.node_matchers: List[NodeMatcher] = []
        for group in content["node_icons"]:
            for element in group["tags"]:
                self.node_matchers.append(NodeMatcher(element))

        self.colors: Dict[str, str] = content["colors"]
        self.material_colors: Dict[str, str] = content["material_colors"]

        self.way_matchers: List[WayMatcher] = [
            WayMatcher(x, self) for x in content["ways"]
        ]
        self.road_matchers: List[RoadMatcher] = [
            RoadMatcher(x, self) for x in content["roads"]
        ]
        self.area_matchers: List[Matcher] = [
            Matcher(x) for x in content["area_tags"]
        ]
        self.tags_to_write: List[str] = content["tags_to_write"]
        self.prefix_to_write: List[str] = content["prefix_to_write"]
        self.tags_to_skip: List[str] = content["tags_to_skip"]
        self.prefix_to_skip: List[str] = content["prefix_to_skip"]

        # Storage for created icon sets.
        self.cache: Dict[str, Tuple[IconSet, int]] = {}

    def get_color(self, color: str) -> Color:
        """
        Return color if the color is in scheme, otherwise return default color.

        :param color: input color string representation
        :return: color specification
        """
        if color in self.colors:
            return Color(self.colors[color])
        if color.lower() in self.colors:
            return Color(self.colors[color.lower()])
        try:
            return Color(color)
        except (ValueError, AttributeError):
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
            if key[: len(prefix) + 1] == f"{prefix}:":
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
        for prefix in self.prefix_to_write:  # type: str
            if key[: len(prefix) + 1] == f"{prefix}:":
                return True
        return False

    def get_icon(
        self,
        icon_extractor: ShapeExtractor,
        tags: Dict[str, Any],
        processed: Set[str],
        for_: str = "node",
    ) -> Tuple[IconSet, int]:
        """
        Construct icon set.

        :param icon_extractor: extractor with icon specifications
        :param tags: OpenStreetMap element tags dictionary
        :param for_: target (node, way, area or relation)
        :param processed: set of already processed tag keys
        :return (icon set, icon priority)
        """
        tags_hash: str = (
            ",".join(tags.keys()) + ":" + ",".join(map(str, tags.values()))
        )
        if tags_hash in self.cache:
            return self.cache[tags_hash]

        main_icon: Optional[Icon] = None
        extra_icons: List[Icon] = []
        priority: int = 0

        index: int = 0

        for matcher in self.node_matchers:
            if not matcher.replace_shapes and main_icon:
                continue
            matched: bool = matcher.is_matched(tags)
            if not matched:
                continue
            matcher_tags: Set[str] = set(matcher.tags.keys())
            priority = len(self.node_matchers) - index
            if not matcher.draw:
                processed |= matcher_tags
            if matcher.shapes:
                main_icon = Icon([
                    ShapeSpecification.from_structure(x, icon_extractor, self)
                    for x in matcher.shapes
                ])
                processed |= matcher_tags
            if matcher.over_icon:
                if main_icon:
                    main_icon.add_specifications([
                        ShapeSpecification.from_structure(
                            x, icon_extractor, self
                        )
                        for x in matcher.over_icon
                    ])
                    processed |= matcher_tags
            if matcher.add_shapes:
                extra_icons += [Icon([
                    ShapeSpecification.from_structure(
                        x, icon_extractor, self, Color("#888888")
                    )
                    for x in matcher.add_shapes
                ])]
                processed |= matcher_tags
            if matcher.set_main_color and main_icon:
                main_icon.recolor(self.get_color(matcher.set_main_color))

            index += 1

        color: Optional[Color] = None

        if "material" in tags:
            value: str = tags["material"]
            if value in self.material_colors:
                color = self.get_color(self.material_colors[value])
                processed.add("material")

        for tag_key in tags:
            if tag_key.endswith(":color") or tag_key.endswith(":colour"):
                color = self.get_color(tags[tag_key])
                processed.add(tag_key)

        for color_tag_key in ["color", "colour"]:
            if color_tag_key in tags:
                color = self.get_color(tags[color_tag_key])
                processed.add(color_tag_key)

        if main_icon and color:
            main_icon.recolor(color)

        keys_left = [
            x
            for x in tags.keys()
            if x not in processed and not self.is_no_drawable(x)
        ]

        default_shape = icon_extractor.get_shape(DEFAULT_SHAPE_ID)
        if not main_icon:
            main_icon = Icon([ShapeSpecification(default_shape)])

        returned: IconSet = IconSet(main_icon, extra_icons, processed)
        self.cache[tags_hash] = returned, priority

        for key in ["direction", "camera:direction"]:
            if key in tags:
                for specification in main_icon.shape_specifications:
                    if (
                        DirectionSet(tags[key]).is_right() is False
                        and specification.shape.is_right_directed is True
                        or specification.shape.is_right_directed is True
                        and specification.shape.is_right_directed is False
                    ):
                        specification.flip_horizontally = True

        return returned, priority

    def get_style(self, tags: Dict[str, Any], scale):
        """
        Get line style based on tags and scale.
        """
        line_styles = []

        for matcher in self.way_matchers:
            if not matcher.is_matched(tags):
                continue

            line_styles.append(LineStyle(matcher.style, matcher.priority))

        return line_styles

    def get_road(self, tags: Dict[str, Any]) -> Optional[RoadMatcher]:
        for matcher in self.road_matchers:
            if not matcher.is_matched(tags):
                continue
            return matcher
        return None

    def construct_text(
        self, tags: Dict[str, str], draw_captions: str, processed: Set[str]
    ) -> List[Label]:
        """
        Construct labels for not processed tags.
        """
        texts: List[Label] = []

        name = None
        alt_name = None
        if "name" in tags:
            name = tags["name"]
            processed.add("name")
        elif "name:en" in tags:
            if not name:
                name = tags["name:en"]
                processed.add("name:en")
            processed.add("name:en")
        if "alt_name" in tags:
            if alt_name:
                alt_name += ", "
            else:
                alt_name = ""
            alt_name += tags["alt_name"]
            processed.add("alt_name")
        if "old_name" in tags:
            if alt_name:
                alt_name += ", "
            else:
                alt_name = ""
            alt_name += "ex " + tags["old_name"]

        address: List[str] = get_address(tags, draw_captions, processed)

        if name:
            texts.append(Label(name, Color("black")))
        if alt_name:
            texts.append(Label(f"({alt_name})"))
        if address:
            texts.append(Label(", ".join(address)))

        if draw_captions == "main":
            return texts

        texts += get_text(tags, processed)

        if "route_ref" in tags:
            texts.append(Label(tags["route_ref"].replace(";", " ")))
            processed.add("route_ref")
        if "cladr:code" in tags:
            texts.append(Label(tags["cladr:code"], size=7))
            processed.add("cladr:code")
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
            processed.add("website")
        for key in ["phone"]:
            if key in tags:
                texts.append(Label(tags[key], Color("#444444")))
                processed.add(key)
        if "height" in tags:
            texts.append(Label(f"↕ {tags['height']} m"))
            processed.add("height")
        for tag in tags:
            if self.is_writable(tag) and tag not in processed:
                texts.append(Label(tags[tag]))
        return texts

    def is_area(self, tags: Dict[str, str]) -> bool:
        """
        Check whether way described by tags is area.
        """
        for matcher in self.area_matchers:
            if matcher.is_matched(tags):
                return True
        return False

    def process_ignored(
        self, tags: Dict[str, str], processed: Set[str]
    ) -> None:
        """
        Mark all ignored tag as processed.

        :param tags: input tag dictionary
        :param processed: processed set
        """
        for tag in tags:
            if self.is_no_drawable(tag):
                processed.add(tag)
