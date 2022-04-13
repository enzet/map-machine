"""
Map Machine drawing scheme.
"""
import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np
import yaml
from colour import Color

from map_machine.feature.direction import DirectionSet
from map_machine.map_configuration import MapConfiguration
from map_machine.osm.osm_reader import Tagged, Tags
from map_machine.pictogram.icon import (
    DEFAULT_SHAPE_ID,
    Icon,
    IconSet,
    Shape,
    ShapeExtractor,
    ShapeSpecification,
    DEFAULT_SMALL_SHAPE_ID,
)

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

IconDescription = List[Union[str, Dict[str, str]]]


@dataclass
class LineStyle:
    """SVG line style and its priority."""

    style: Dict[str, Union[int, float, str]]
    parallel_offset: float = 0.0
    priority: float = 0.0


class MatchingType(Enum):
    """Description on how tag was matched."""

    NOT_MATCHED = 0
    MATCHED_BY_SET = 1
    MATCHED_BY_WILDCARD = 2
    MATCHED = 3
    MATCHED_BY_REGEX = 4


def is_matched_tag(
    matcher_tag_key: str,
    matcher_tag_value: Union[str, list],
    tags: Tags,
) -> Tuple[MatchingType, List[str]]:
    """
    Check whether element tags contradict tag matcher.

    :param matcher_tag_key: tag key
    :param matcher_tag_value: tag value, tag value list, or "*"
    :param tags: element tags to check
    """
    if matcher_tag_key not in tags:
        return MatchingType.NOT_MATCHED, []

    if matcher_tag_value == "*":
        return MatchingType.MATCHED_BY_WILDCARD, []
    if tags[matcher_tag_key] == matcher_tag_value:
        return MatchingType.MATCHED, []
    if matcher_tag_value.startswith("^"):
        matcher: Optional[re.Match] = re.match(
            matcher_tag_value, tags[matcher_tag_key]
        )
        if matcher:
            return MatchingType.MATCHED_BY_REGEX, list(matcher.groups())

    return MatchingType.NOT_MATCHED, []


def get_selector(key: str, value: str, prefix: str = "") -> str:
    """Get MapCSS 0.2 selector for one key."""
    if prefix:
        key = f"{prefix}:{key}"
    if value == "*":
        return f"[{key}]"
    if '"' in value:
        return f"[{key}='{value}']"
    return f'[{key}="{value}"]'


def match_location(restrictions: Dict[str, str], country: str) -> bool:
    """Check whether country is matched by location restrictions."""
    if "exclude" in restrictions and country in restrictions["exclude"]:
        return False
    if (
        "include" in restrictions
        and restrictions["include"] != "world"
        and country not in restrictions["include"]
    ):
        return False
    return True


class Matcher(Tagged):
    """Tag matching."""

    def __init__(
        self, structure: Dict[str, Any], group: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(structure["tags"])

        self.exception: Dict[str, str] = {}
        if "exception" in structure:
            self.exception = structure["exception"]

        self.start_zoom_level: Optional[int] = None
        if group is not None and "start_zoom_level" in group:
            self.start_zoom_level = group["start_zoom_level"]

        self.replace_shapes: bool = True
        if "replace_shapes" in structure:
            self.replace_shapes = structure["replace_shapes"]

        self.location_restrictions: Dict[str, str] = {}
        if "location_restrictions" in structure:
            self.location_restrictions = structure["location_restrictions"]

        self.verify()

    def check_zoom_level(self, zoom_level: float) -> bool:
        """Check whether zoom level is matching."""
        return (
            self.start_zoom_level is None or zoom_level >= self.start_zoom_level
        )

    def is_matched(
        self, tags: Tags, configuration: Optional[MapConfiguration] = None
    ) -> Tuple[bool, Dict[str, str]]:
        """
        Check whether element tags matches tag matcher.

        :param tags: element tags to be matched
        :param configuration: current map configuration to be matched
        """
        groups: Dict[str, str] = {}

        if (
            configuration is not None
            and self.location_restrictions
            and not match_location(
                self.location_restrictions, configuration.country
            )
        ):
            return False, {}

        for config_tag_key in self.tags:
            config_tag_key: str
            is_matched, matched_groups = is_matched_tag(
                config_tag_key, self.tags[config_tag_key], tags
            )
            if is_matched == MatchingType.NOT_MATCHED:
                return False, {}

            if matched_groups:
                for index, element in enumerate(matched_groups):
                    groups[f"#{config_tag_key}{index}"] = element

        if self.exception:
            for config_tag_key in self.exception:
                config_tag_key: str
                is_matched, matched_groups = is_matched_tag(
                    config_tag_key, self.exception[config_tag_key], tags
                )
                if is_matched != MatchingType.NOT_MATCHED:
                    return False, {}

        return True, groups

    def get_mapcss_selector(self, prefix: str = "") -> str:
        """
        Construct MapCSS 0.2 selector from the node matcher.

        See https://wiki.openstreetmap.org/wiki/MapCSS/0.2
        """
        return "".join(
            [get_selector(x, y, prefix) for (x, y) in self.tags.items()]
        )

    def get_clean_shapes(self) -> Optional[List[str]]:
        """Get list of shape identifiers for shapes."""
        return None

    def get_style(self) -> Dict[str, Any]:
        """Return way SVG style."""
        return {}


def get_shape_specifications(
    structure: List[Union[str, Dict[str, Any]]]
) -> List[dict]:
    """Parse shape specification from scheme."""
    shapes: List[dict] = []
    for shape_specification in structure:
        if isinstance(shape_specification, str):
            shapes.append({"shape": shape_specification})
        else:
            shapes.append(shape_specification)
    return shapes


class NodeMatcher(Matcher):
    """Tag specification matcher."""

    def __init__(
        self, structure: Dict[str, Any], group: Dict[str, Any]
    ) -> None:
        # Dictionary with tag keys and values, value lists, or "*"
        super().__init__(structure, group)

        self.draw: bool = True
        if "draw" in structure:
            self.draw = structure["draw"]

        self.shapes: Optional[IconDescription] = None
        if "shapes" in structure:
            self.shapes = get_shape_specifications(structure["shapes"])

        self.over_icon: Optional[IconDescription] = None
        if "over_icon" in structure:
            self.over_icon = get_shape_specifications(structure["over_icon"])

        self.add_shapes: Optional[IconDescription] = None
        if "add_shapes" in structure:
            self.add_shapes = get_shape_specifications(structure["add_shapes"])

        self.set_main_color: Optional[str] = None
        if "set_main_color" in structure:
            self.set_main_color = structure["set_main_color"]

        self.set_opacity: Optional[float] = None
        if "set_opacity" in structure:
            self.set_opacity = structure["set_opacity"]

        self.under_icon: Optional[IconDescription] = None
        if "under_icon" in structure:
            self.under_icon = get_shape_specifications(structure["under_icon"])

        self.with_icon: Optional[IconDescription] = None
        if "with_icon" in structure:
            self.with_icon = get_shape_specifications(structure["with_icon"])

    def get_clean_shapes(self) -> Optional[List[str]]:
        """Get list of shape identifiers for shapes."""
        if not self.shapes:
            return None
        return [x["shape"] for x in self.shapes]


class WayMatcher(Matcher):
    """Special tag matcher for ways."""

    def __init__(self, structure: Dict[str, Any], scheme: "Scheme") -> None:
        super().__init__(structure)
        self.style: Dict[str, Any] = {"fill": "none"}
        if "style" in structure:
            style: Dict[str, Any] = structure["style"]
            for key in style:
                if str(style[key]).endswith("_color"):
                    self.style[key] = scheme.get_color(style[key]).hex.upper()
                else:
                    self.style[key] = style[key]

        self.priority: float = 0.0
        if "priority" in structure:
            self.priority = structure["priority"]

        self.parallel_offset: float = 0.0
        if parallel_offset := structure.get("parallel_offset"):
            self.parallel_offset = parallel_offset

    def get_style(self) -> Dict[str, Any]:
        """Return way SVG style."""
        return self.style


class RoadMatcher(Matcher):
    """Special tag matcher for highways."""

    def __init__(self, structure: Dict[str, Any], scheme: "Scheme") -> None:
        super().__init__(structure)
        self.border_color: Color = Color(
            scheme.get_color(structure["border_color"])
        )
        self.color: Color = scheme.get_color("road_color")
        if "color" in structure:
            self.color = Color(scheme.get_color(structure["color"]))
        self.default_width: float = structure["default_width"]
        self.priority: float = 0.0
        if "priority" in structure:
            self.priority = structure["priority"]

    def get_priority(self, tags: Tags) -> float:
        """Get priority for drawing order."""
        layer: float = 0.0
        if "layer" in tags:
            layer = float(tags.get("layer"))
        return 1000.0 * layer + self.priority


class Scheme:
    """
    Map style.

    Specifies map colors and rules to draw icons for OpenStreetMap tags.
    """

    def __init__(self, content: Dict[str, Any]) -> None:
        self.node_matchers: List[NodeMatcher] = []
        if "node_icons" in content:
            for group in content["node_icons"]:
                for element in group["tags"]:
                    self.node_matchers.append(NodeMatcher(element, group))

        self.colors: Dict[str, str] = (
            content["colors"] if "colors" in content else {}
        )
        self.material_colors: Dict[str, str] = (
            content["material_colors"] if "material_colors" in content else {}
        )

        self.way_matchers: List[WayMatcher] = (
            [WayMatcher(x, self) for x in content["ways"]]
            if "ways" in content
            else []
        )
        self.road_matchers: List[RoadMatcher] = (
            [RoadMatcher(x, self) for x in content["roads"]]
            if "roads" in content
            else []
        )
        self.area_matchers: List[Matcher] = (
            [Matcher(x) for x in content["area_tags"]]
            if "area_tags" in content
            else []
        )
        self.keys_to_write: List[str] = (
            content["keys_to_write"] if "keys_to_write" in content else []
        )
        self.prefix_to_write: List[str] = (
            content["prefix_to_write"] if "prefix_to_write" in content else []
        )
        self.keys_to_skip: List[str] = (
            content["keys_to_skip"] if "keys_to_skip" in content else []
        )
        self.prefix_to_skip: List[str] = (
            content["prefix_to_skip"] if "prefix_to_skip" in content else []
        )
        self.tags_to_skip: Dict[str, str] = (
            content["tags_to_skip"] if "tags_to_skip" in content else {}
        )

        # Storage for created icon sets.
        self.cache: Dict[str, Tuple[IconSet, int]] = {}

    @classmethod
    def from_file(cls, file_name: Path) -> "Scheme":
        """
        :param file_name: name of the scheme file with tags, colors, and tag key
            specification
        """
        with file_name.open(encoding="utf-8") as input_file:
            content: Dict[str, Any] = yaml.load(
                input_file.read(), Loader=yaml.FullLoader
            )
            return cls(content)

    def get_color(self, color: str) -> Color:
        """
        Return color if the color is in scheme, otherwise return default color.

        :param color: input color string representation
        :return: color specification
        """
        if color in self.colors:
            specification: Union[str, dict] = self.colors[color]
            if isinstance(specification, str):
                return Color(self.colors[color])

            color: Color = self.get_color(specification["color"])
            if "darken" in specification:
                percent: float = float(specification["darken"])
                color.set_luminance(color.get_luminance() * (1 - percent))
            return color

        if color.lower() in self.colors:
            return Color(self.colors[color.lower()])

        try:
            return Color(color)
        except (ValueError, AttributeError):
            logging.debug(f"Unknown color `{color}`.")
            return Color(self.colors["default"])

    def get_default_color(self) -> Color:
        """Get default color for a main icon."""
        return self.get_color("default")

    def get_extra_color(self) -> Color:
        """Get default color for an extra icon."""
        return self.get_color("extra")

    def get(self, variable_name: str):
        """
        FIXME: colors should be variables.
        """
        if variable_name in self.colors:
            return self.colors[variable_name]
        return 0.0

    def is_no_drawable(self, key: str, value: str) -> bool:
        """
        Return true if key is specified as no drawable (should not be
        represented on the map as icon set or as text) by the scheme.

        :param key: OpenStreetMap tag key
        :param value: OpenStreetMap tag value
        """
        if (
            key in self.keys_to_write + self.keys_to_skip
            or key in self.tags_to_skip
            and self.tags_to_skip[key] == value
        ):
            return True

        if ":" in key:
            prefix: str = key.split(":")[0]
            if prefix in self.prefix_to_write + self.prefix_to_skip:
                return True

        return False

    def is_writable(self, key: str, value: str) -> bool:
        """
        Return true if key is specified as writable (should be represented on
        the map as text) by the scheme.

        :param key: OpenStreetMap tag key
        :param value: OpenStreetMap tag value
        """
        if (
            key in self.keys_to_skip
            or key in self.tags_to_skip
            and self.tags_to_skip[key] == value
        ):
            return False

        if key in self.keys_to_write:
            return True

        prefix: Optional[str] = None
        if ":" in key:
            prefix = key.split(":")[0]

        if prefix in self.prefix_to_skip:
            return False

        if prefix in self.prefix_to_write:
            return True

        return False

    def get_icon(
        self,
        extractor: ShapeExtractor,
        tags: Dict[str, Any],
        processed: Set[str],
        configuration: MapConfiguration = MapConfiguration(),
    ) -> Tuple[Optional[IconSet], int]:
        """
        Construct icon set.

        :param extractor: extractor with icon specifications
        :param tags: OpenStreetMap element tags dictionary
        :param processed: set of already processed tag keys
        :param configuration: current map configuration to be matched
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
        color: Optional[Color] = None

        for index, matcher in enumerate(self.node_matchers):
            if not matcher.replace_shapes and main_icon:
                continue
            matching, groups = matcher.is_matched(tags, configuration)
            if not matching:
                continue
            if (
                not configuration.ignore_level_matching
                and not matcher.check_zoom_level(configuration.zoom_level)
            ):
                return None, 0
            matcher_tags: Set[str] = set(matcher.tags.keys())
            priority = len(self.node_matchers) - index
            if not matcher.draw:
                processed |= matcher_tags
            if matcher.shapes:
                specifications = [
                    self.get_shape_specification(x, extractor, groups)
                    for x in matcher.shapes
                ]
                main_icon = Icon(specifications)
                processed |= matcher_tags
            if matcher.over_icon and main_icon:
                specifications = [
                    self.get_shape_specification(x, extractor)
                    for x in matcher.over_icon
                ]
                main_icon.add_specifications(specifications)
                processed |= matcher_tags
            if matcher.add_shapes:
                specifications = [
                    self.get_shape_specification(
                        x, extractor, color=self.get_extra_color()
                    )
                    for x in matcher.add_shapes
                ]
                extra_icons += [Icon(specifications)]
                processed |= matcher_tags
            if matcher.set_main_color and main_icon:
                color = self.get_color(matcher.set_main_color)
            if matcher.set_opacity and main_icon:
                main_icon.opacity = matcher.set_opacity

        if "material" in tags:
            value: str = tags["material"]
            if value in self.material_colors:
                color = self.get_color(self.material_colors[value])
                processed.add("material")

        for tag_key in tags:
            if tag_key.endswith(":color") or tag_key.endswith(":colour"):
                color = self.get_color(tags[tag_key])
                processed.add(tag_key)

        for color_tag_key in ["colour", "color", "building:colour"]:
            if color_tag_key in tags:
                color = self.get_color(tags[color_tag_key])
                processed.add(color_tag_key)

        if not main_icon:
            dot_spec: ShapeSpecification = ShapeSpecification(
                extractor.get_shape(DEFAULT_SHAPE_ID), self.get_color("default")
            )
            main_icon: Icon = Icon([dot_spec])

        if main_icon and color:
            main_icon.recolor(color)

        default_icon: Optional[Icon] = None
        if configuration.show_overlapped:
            small_dot_spec: ShapeSpecification = ShapeSpecification(
                extractor.get_shape(DEFAULT_SMALL_SHAPE_ID),
                color if color else self.get_color("default"),
            )
            default_icon = Icon([small_dot_spec])

        returned: IconSet = IconSet(
            main_icon, extra_icons, default_icon, processed
        )
        self.cache[tags_hash] = returned, priority

        for key in "direction", "camera:direction":
            if key in tags:
                for specification in main_icon.shape_specifications:
                    if (
                        DirectionSet(tags[key]).is_right() is not None
                        and specification.shape.is_right_directed is not None
                        and DirectionSet(tags[key]).is_right()
                        != specification.shape.is_right_directed
                    ):
                        specification.flip_horizontally = True

        return returned, priority

    def get_style(self, tags: Dict[str, Any]) -> List[LineStyle]:
        """Get line style based on tags and scale."""
        line_styles = []

        for matcher in self.way_matchers:
            matching, _ = matcher.is_matched(tags)
            if not matching:
                continue

            line_style: LineStyle = LineStyle(
                matcher.style, matcher.parallel_offset, matcher.priority
            )
            line_styles.append(line_style)

        return line_styles

    def get_road(self, tags: Dict[str, Any]) -> Optional[RoadMatcher]:
        """Get road matcher if tags are matched."""
        for matcher in self.road_matchers:
            matching, _ = matcher.is_matched(tags)
            if not matching:
                continue
            return matcher
        return None

    def is_area(self, tags: Tags) -> bool:
        """Check whether way described by tags is area."""
        for matcher in self.area_matchers:
            matching, _ = matcher.is_matched(tags)
            if matching:
                return True
        return False

    def process_ignored(self, tags: Tags, processed: Set[str]) -> None:
        """
        Mark all ignored tag as processed.

        :param tags: input tag dictionary
        :param processed: processed set
        """
        processed.update(
            set(tag for tag in tags if self.is_no_drawable(tag, tags[tag]))
        )

    def get_shape_specification(
        self,
        structure: Union[str, Dict[str, Any]],
        extractor: ShapeExtractor,
        groups: Dict[str, str] = None,
        color: Optional[Color] = None,
    ) -> ShapeSpecification:
        """
        Parse shape specification from structure, that is just shape string
        identifier or dictionary with keys: shape (required), color (optional),
        and offset (optional).
        """
        shape: Shape = extractor.get_shape(DEFAULT_SHAPE_ID)
        color: Color = (
            color if color is not None else Color(self.colors["default"])
        )
        offset: np.ndarray = np.array((0.0, 0.0))
        flip_horizontally: bool = False
        flip_vertically: bool = False
        use_outline: bool = True

        structure: Dict[str, Any]
        if "shape" in structure:
            shape_id: str = structure["shape"]
            if groups:
                for key in groups:
                    shape_id = shape_id.replace(key, groups[key])
            shape = extractor.get_shape(shape_id)
        else:
            logging.error("Invalid shape specification: `shape` key expected.")
        if "color" in structure:
            color = self.get_color(structure["color"])
        if "offset" in structure:
            offset = np.array(structure["offset"])
        if "flip_horizontally" in structure:
            flip_horizontally = structure["flip_horizontally"]
        if "flip_vertically" in structure:
            flip_vertically = structure["flip_vertically"]
        if "outline" in structure:
            use_outline = structure["outline"]

        return ShapeSpecification(
            shape,
            color,
            offset,
            flip_horizontally,
            flip_vertically,
            use_outline,
        )
