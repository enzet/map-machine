"""Map Machine drawing scheme."""

from __future__ import annotations

import contextlib
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, cast

import yaml
from colour import Color
from roentgen.icon import IconSpecification, ShapeSpecification

from map_machine.feature.direction import DirectionSet
from map_machine.map_configuration import (
    BuildingMode,
    DrawingMode,
    LabelMode,
    RoadMode,
)
from map_machine.osm.osm_reader import Tagged, Tags
from map_machine.pictogram.icon import (
    DEFAULT_SHAPE_ID,
    DEFAULT_SMALL_SHAPE_ID,
    IconSet,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

__author__ = "Sergey Vartanov"
__email__ = "me@enzet.ru"

logger: logging.Logger = logging.getLogger(__name__)

IconDescription = list[dict[str, str]]

DEFAULT_COLOR: Color = Color("black")


@dataclass
class LineStyle:
    """SVG line style and its priority."""

    style: dict[str, int | float | str]
    parallel_offset: float = 0.0
    priority: float = 0.0


class MatchingType(Enum):
    """Description of how a tag was matched."""

    NOT_MATCHED = 0
    MATCHED_BY_SET = 1
    MATCHED_BY_WILDCARD = 2
    MATCHED = 3
    MATCHED_BY_REGEX = 4


def is_matched_tag(
    matcher_tag_key: str,
    matcher_tag_value: str | list,
    tags: Tags,
) -> tuple[MatchingType, list[str]]:
    """Check whether element tags contradict tag matcher.

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
    if (
        isinstance(matcher_tag_value, list)
        and tags[matcher_tag_key] in matcher_tag_value
    ):
        return MatchingType.MATCHED, []
    if isinstance(matcher_tag_value, str) and matcher_tag_value.startswith("^"):
        matcher: re.Match | None = re.match(
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


def match_location(restrictions: dict[str, str], country: str) -> bool:
    """Check whether country is matched by location restrictions."""
    if "exclude" in restrictions and country in restrictions["exclude"]:
        return False
    return not (
        "include" in restrictions
        and restrictions["include"] != "world"
        and country not in restrictions["include"]
    )


@dataclass
class Matcher(Tagged):
    """Tag matching."""

    exception: dict[str, str] = field(default_factory=dict)
    start_zoom_level: int | None = None
    replace_shapes: bool = True
    location_restrictions: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_structure(
        cls,
        structure: dict[str, Any],
        scheme: Scheme,  # noqa: ARG003
    ) -> Matcher:
        """Initialize matcher from structure."""

        matcher = cls(tags=structure["tags"])

        matcher.exception = structure.get("exception", {})
        matcher.start_zoom_level = structure.get("start_zoom_level")
        matcher.replace_shapes = structure.get("replace_shapes", True)
        matcher.location_restrictions = structure.get(
            "location_restrictions", {}
        )

        matcher.verify()

        return matcher

    def check_zoom_level(self, zoom_level: float) -> bool:
        """Check whether zoom level is matching."""
        return (
            self.start_zoom_level is None or zoom_level >= self.start_zoom_level
        )

    def is_matched(
        self, tags: Tags, country: str | None = None
    ) -> tuple[bool, dict[str, str]]:
        """Check whether element tags match the tag matcher.

        :param tags: element tags to be matched
        :param country: country of the element (to match location restrictions
            if any)
        """
        groups: dict[str, str] = {}

        if (
            country is not None
            and self.location_restrictions
            and not match_location(self.location_restrictions, country)
        ):
            return False, {}

        for config_tag_key in self.tags:
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
                is_matched, matched_groups = is_matched_tag(
                    config_tag_key, self.exception[config_tag_key], tags
                )
                if is_matched != MatchingType.NOT_MATCHED:
                    return False, {}

        return True, groups

    def get_mapcss_selector(self, prefix: str = "") -> str:
        """Construct MapCSS 0.2 selector from the node matcher.

        See https://wiki.openstreetmap.org/wiki/MapCSS/0.2
        """
        return "".join(
            [get_selector(x, y, prefix) for (x, y) in self.tags.items()]
        )

    def get_clean_shapes(self) -> list[str] | None:
        """Get list of shape identifiers for shapes."""
        return None

    def get_style(self) -> dict[str, Any]:
        """Return way SVG style."""
        return {}


def get_shape_specifications(
    structure: list[str | dict[str, Any]],
) -> list[dict[str, Any]]:
    """Parse shape specification from scheme."""
    shapes: list[dict] = []
    for shape_specification in structure:
        if isinstance(shape_specification, str):
            shapes.append({"shape": shape_specification})
        else:
            shapes.append(shape_specification)
    return shapes


@dataclass
class NodeMatcher(Matcher):
    """Tag specification matcher."""

    draw: bool = True
    shapes: IconDescription | None = None
    over_icon: IconDescription | None = None
    under_icon: IconDescription | None = None
    with_icon: IconDescription | None = None
    add_shapes: IconDescription | None = None
    set_main_color: str | None = None

    @classmethod
    def from_structure(
        cls, structure: dict[str, Any], scheme: Scheme
    ) -> NodeMatcher:
        """Initialize node matcher from structure."""

        node_matcher: NodeMatcher = cast(
            "NodeMatcher", super().from_structure(structure, scheme)
        )

        node_matcher.draw = structure.get("draw", True)
        node_matcher.shapes = get_shape_specifications(
            structure.get("shapes", [])
        )
        node_matcher.over_icon = get_shape_specifications(
            structure.get("over_icon", [])
        )
        node_matcher.under_icon = get_shape_specifications(
            structure.get("under_icon", [])
        )
        node_matcher.with_icon = get_shape_specifications(
            structure.get("with_icon", [])
        )
        node_matcher.add_shapes = get_shape_specifications(
            structure.get("add_shapes", [])
        )

        node_matcher.set_main_color = structure.get("set_main_color")

        return node_matcher

    def get_clean_shapes(self) -> list[str] | None:
        """Get list of shape identifiers for shapes."""
        if not self.shapes:
            return None
        return [x["shape"] for x in self.shapes if "shape" in x]


@dataclass
class WayMatcher(Matcher):
    """Special tag matcher for ways."""

    style: dict[str, Any] = field(default_factory=dict)
    priority: float = 0.0
    parallel_offset: float = 0.0

    @classmethod
    def from_structure(
        cls, structure: dict[str, Any], scheme: Scheme
    ) -> WayMatcher:
        """Initialize way matcher from structure."""
        way_matcher: WayMatcher = cast(
            "WayMatcher", super().from_structure(structure, scheme)
        )

        way_matcher.style = {"fill": "none"}
        if "style" in structure:
            style: dict[str, Any] = structure["style"]
            for key, value in style.items():
                if str(value).startswith("$"):
                    if key in ("fill", "stroke"):
                        way_matcher.style[key] = scheme.get_color(
                            value
                        ).hex.upper()
                    else:
                        way_matcher.style[key] = scheme.get_variable(value)
                else:
                    way_matcher.style[key] = value

        way_matcher.priority = structure.get("priority", 0.0)
        way_matcher.parallel_offset = structure.get("parallel_offset", 0.0)

        return way_matcher

    def get_style(self) -> dict[str, Any]:
        """Return way SVG style."""
        return self.style


@dataclass
class RoadMatcher(Matcher):
    """Special tag matcher for highways."""

    border_color: Color | None = None
    color: Color | None = None
    default_width: float | None = None
    priority: float = 0.0

    @classmethod
    def from_structure(
        cls, structure: dict[str, Any], scheme: Scheme
    ) -> RoadMatcher:
        """Initialize road matcher from structure."""
        road_matcher: RoadMatcher = cast(
            "RoadMatcher", super().from_structure(structure, scheme)
        )

        road_matcher.border_color = Color(
            scheme.get_color(structure["border_color"])
        )
        road_matcher.color = scheme.get_color("$road_color")
        if "color" in structure:
            road_matcher.color = Color(scheme.get_color(structure["color"]))
        road_matcher.default_width = structure["default_width"]
        road_matcher.priority = structure.get("priority", 0.0)
        return road_matcher

    def get_priority(self, tags: Tags) -> float:
        """Get priority for drawing order."""
        layer: float = 0.0
        layer_value: str | None = tags.get("layer")
        if layer_value is not None:
            with contextlib.suppress(ValueError, TypeError):
                layer = float(layer_value)
        return 1000.0 * layer + self.priority


def _merge_contents(
    base: dict[str, Any], overlay: dict[str, Any]
) -> dict[str, Any]:
    """Merge two scheme content dicts.

    Lists are concatenated, dicts are merged (overlay wins on key
    conflicts), and scalar values are overridden by the overlay.
    """
    merged: dict[str, Any] = {}
    for key in set(base) | set(overlay):
        if key not in overlay:
            merged[key] = base[key]
        elif key not in base:
            merged[key] = overlay[key]
        elif isinstance(base[key], list) and isinstance(overlay[key], list):
            merged[key] = base[key] + overlay[key]
        elif isinstance(base[key], dict) and isinstance(overlay[key], dict):
            merged[key] = {**base[key], **overlay[key]}
        else:
            merged[key] = overlay[key]
    return merged


def _load_with_includes(
    file_name: Path,
    find_scheme_path: Callable[[str], Path | None] | None = None,
) -> dict[str, Any]:
    """Load a scheme YAML file, recursively resolving `include`.

    :param file_name: path to the YAML scheme file.
    :param find_scheme_path: callback that resolves a scheme identifier
        (e.g. `"default"`) to a file path.
    """
    with file_name.open(encoding="utf-8") as input_file:
        content: dict[str, Any] = yaml.safe_load(input_file.read())
        if not content:
            message: str = f"Scheme file {file_name} is empty."
            raise ValueError(message)

    includes: list[str] = content.pop("include", [])
    if isinstance(includes, str):
        includes = [includes]

    base: dict[str, Any] = {}
    for identifier in includes:
        path: Path | None = None
        if find_scheme_path is not None:
            path = find_scheme_path(identifier)
        if path is None:
            path = file_name.parent / f"{identifier}.yml"
        if not path.is_file():
            message = f"Included scheme `{identifier}` not found."
            raise FileNotFoundError(message)
        base = _merge_contents(
            base, _load_with_includes(path, find_scheme_path)
        )

    return _merge_contents(base, content)


def _yaml_str(value: bool | str | float) -> str:  # noqa: FBT001
    """Convert a YAML value to string.

    YAML parses bare `no` as `False` and `yes` as `True`. This function converts
    booleans back to their string representation so that they can be used with
    `Enum(value)` constructors.
    """
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


class Scheme:
    """Map style.

    Specifies map colors and rules to draw icons for OpenStreetMap tags.
    """

    def __init__(self, content: dict[str, Any]) -> None:
        self.node_matchers: list[NodeMatcher] = []
        if "nodes" in content:
            for group in content["nodes"]:
                for element in group["tags"]:
                    self.node_matchers.append(
                        NodeMatcher.from_structure(element, group)
                    )

        options = content.get("options", {})

        self.nodes: bool = options.get("nodes", False)
        self.trees: bool = options.get("trees", False)
        self.craters: bool = options.get("craters", False)
        self.directions: bool = options.get("directions", False)

        self.building_mode: BuildingMode = BuildingMode(
            _yaml_str(options.get("buildings", "flat"))
        )
        self.road_mode: RoadMode = RoadMode(
            _yaml_str(options.get("roads", "simple"))
        )
        self.drawing_mode: DrawingMode = DrawingMode(
            _yaml_str(options.get("mode", "normal"))
        )
        self.label_mode: LabelMode = LabelMode(
            _yaml_str(options.get("labels", "main"))
        )

        self.roofs: bool = options.get("roofs", True)
        self.building_colors: bool = options.get("building_colors", False)
        self.background: bool = options.get("background", True)

        self.variables: dict[str, str] = content.get("variables", {})
        self.variables.update(content.get("material_colors", {}))

        self.way_matchers: list[WayMatcher] = (
            [WayMatcher.from_structure(x, self) for x in content["ways"]]
            if "ways" in content
            else []
        )
        self.road_matchers: list[RoadMatcher] = (
            [RoadMatcher.from_structure(x, self) for x in content["roads"]]
            if "roads" in content
            else []
        )
        self.area_matchers: list[Matcher] = (
            [Matcher.from_structure(x, self) for x in content["area_tags"]]
            if "area_tags" in content
            else []
        )
        self.keys_to_write: list[str] = content.get("keys_to_write", [])
        self.prefix_to_write: list[str] = content.get("prefix_to_write", [])
        self.keys_to_skip: list[str] = content.get("keys_to_skip", [])
        self.prefix_to_skip: list[str] = content.get("prefix_to_skip", [])
        self.tags_to_skip: dict[str, str] = content.get("tags_to_skip", {})

        # Storage for created icon sets.
        self.cache: dict[str, tuple[IconSet, int]] = {}

    @classmethod
    def from_file(
        cls,
        file_name: Path,
        find_scheme_path: Callable[[str], Path | None] | None = None,
    ) -> Scheme:
        """Get scheme from file.

        :param file_name: name of the scheme file with tags, variables, and
            tag key specification
        :param find_scheme_path: optional callback that resolves a scheme
            identifier to a file path (used to resolve `include`
            entries)
        """
        content = _load_with_includes(file_name, find_scheme_path)
        return cls(content)

    def get_variable(self, variable_name: str) -> Any:  # noqa: ANN401
        """Get variable value."""
        return self.variables[variable_name[1:]]

    def get_color(self, color_specification: str | dict) -> Color:
        """Get any color.

        If `color_string` starts with `$`, strip the prefix and look up the
        name in :pyattr:`variables`.  Otherwise treat it as a literal color
        (CSS name or hexidecimal value).

        :param color_string: input color string representation
        :return: color specification
        """
        if isinstance(color_specification, dict):
            color: Color = self.get_color(color_specification["color"])
            if "darken" in color_specification:
                percent: float = float(color_specification["darken"])
                color.set_luminance(color.get_luminance() * (1 - percent))
            if "lighten" in color_specification:
                percent: float = float(color_specification["lighten"])
                color.set_luminance(color.get_luminance() * (1 + percent))
            return color

        if color_specification.startswith("$"):
            name: str = color_specification[1:]
            if name in self.variables:
                specification: str | dict = self.variables[name]
                return self.get_color(specification)

        try:
            return Color(color_specification)
        except (ValueError, AttributeError):
            logger.debug("Unknown color `%s`.", color_specification)
            if "default" in self.variables:
                return Color(self.variables["default"])
            return DEFAULT_COLOR

    def get_default_color(self) -> Color:
        """Get default color for a main icon."""
        return self.get_color("$default")

    def get_extra_color(self) -> Color:
        """Get default color for an extra icon."""
        return self.get_color("$extra")

    def get(self, variable_name: str) -> str | float:
        """Get value of variable."""
        if variable_name in self.variables:
            return self.variables[variable_name]
        return 0.0

    def is_no_drawable(self, key: str, value: str) -> bool:
        """Check whether the tag is not drawable.

        Return true if the key is specified as non-drawable (should not be
        represented on the map as an icon set or as text) by the scheme.

        :param key: OpenStreetMap tag key
        :param value: OpenStreetMap tag value
        """
        if key in self.keys_to_write + self.keys_to_skip or (
            key in self.tags_to_skip and self.tags_to_skip[key] == value
        ):
            return True

        if ":" in key:
            prefix: str = key.split(":")[0]
            if prefix in self.prefix_to_write + self.prefix_to_skip:
                return True

        return False

    def is_writable(self, key: str, value: str) -> bool:
        """Check whether the tag is writable.

        Return true if the key is specified as writable (should be represented
        on the map as text) by the scheme.

        :param key: OpenStreetMap tag key
        :param value: OpenStreetMap tag value
        """
        if key in self.keys_to_skip or (
            key in self.tags_to_skip and self.tags_to_skip[key] == value
        ):
            return False

        if key in self.keys_to_write:
            return True

        prefix: str | None = None
        if ":" in key:
            prefix = key.split(":")[0]

        if prefix in self.prefix_to_skip:
            return False

        return prefix in self.prefix_to_write

    def get_icon(
        self,
        tags: dict[str, Any],
        processed: set[str],
        country: str | None = None,
        zoom_level: float = 18,
        *,
        ignore_level_matching: bool = False,
        show_overlapped: bool = False,
    ) -> tuple[IconSet | None, int]:
        """Construct icon set.

        :param roentgen: Röntgen instance with icon specifications
        :param tags: OpenStreetMap element tags dictionary
        :param processed: set of already processed tag keys
        :param country: country to match location restrictions
        :param zoom_level: current map zoom level
        :param ignore_level_matching: do not check level for the icon
        :param show_overlapped: get small dot instead of icon if point is
            overlapped by some other points
        :return (icon set, icon priority)
        """
        tags_hash: str = (
            ",".join(tags.keys()) + ":" + ",".join(map(str, tags.values()))
        )
        if tags_hash in self.cache:
            return self.cache[tags_hash]

        main_icon: IconSpecification | None = None
        extra_icons: list[IconSpecification] = []
        priority: int = 0
        color: Color | None = None

        for index, matcher in enumerate(self.node_matchers):
            if not matcher.replace_shapes and main_icon:
                continue
            matching, groups = matcher.is_matched(tags, country)
            if not matching:
                continue
            if not ignore_level_matching and not matcher.check_zoom_level(
                zoom_level
            ):
                return None, 0
            matcher_tags: set[str] = set(matcher.tags.keys())
            priority = len(self.node_matchers) - index
            if not matcher.draw:
                processed |= matcher_tags
            if matcher.shapes:
                specifications = [
                    self.get_shape_specification(x, groups)
                    for x in matcher.shapes
                ]
                main_icon = IconSpecification("", specifications, "")
                processed |= matcher_tags
            if matcher.over_icon and main_icon:
                specifications = [
                    self.get_shape_specification(x) for x in matcher.over_icon
                ]
                main_icon.add_specifications(specifications)
                processed |= matcher_tags
            if matcher.add_shapes:
                specifications = [
                    self.get_shape_specification(
                        x, color=self.get_extra_color()
                    )
                    for x in matcher.add_shapes
                ]
                extra_icons += [IconSpecification("", specifications, "")]
                processed |= matcher_tags
            if matcher.set_main_color and main_icon:
                color = self.get_color(matcher.set_main_color)

        if "material" in tags:
            value: str = tags["material"]
            if value in self.variables:
                color = self.get_color(f"${value}")
                processed.add("material")

        for tag_key, tag_value in tags.items():
            if tag_key.endswith((":color", ":colour")):
                color = self.get_color(tag_value)
                processed.add(tag_key)

        for color_tag_key in ["colour", "color", "building:colour"]:
            if color_tag_key in tags:
                color = self.get_color(tags[color_tag_key])
                processed.add(color_tag_key)

        if not main_icon:
            dot_spec: ShapeSpecification = ShapeSpecification(
                DEFAULT_SHAPE_ID, color=self.get_color("$default")
            )
            main_icon = IconSpecification("", [dot_spec], "")

        if color:
            main_icon.recolor(color)

        default_icon: IconSpecification | None = None
        if show_overlapped:
            small_dot_spec: ShapeSpecification = ShapeSpecification(
                DEFAULT_SMALL_SHAPE_ID,
                color=color if color else self.get_color("$default"),
            )
            default_icon = IconSpecification("", [small_dot_spec], "")

        returned: IconSet = IconSet(
            main_icon, extra_icons, default_icon, processed
        )
        self.cache[tags_hash] = returned, priority

        for key in "direction", "camera:direction":
            if key in tags:
                for specification in main_icon.shape_specifications:
                    if not DirectionSet(tags[key]).is_right():
                        specification.flip_horizontally = True

        return returned, priority

    def get_style(self, tags: dict[str, Any]) -> list[LineStyle]:
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

    def get_road(self, tags: dict[str, Any]) -> RoadMatcher | None:
        """Get road matcher if tags are matched."""
        for matcher in self.road_matchers:
            matching, _ = matcher.is_matched(tags)
            if not matching:
                continue
            return matcher
        return None

    def is_area(self, tags: Tags) -> bool:
        """Check whether the way described by tags is an area."""
        for matcher in self.area_matchers:
            matching, _ = matcher.is_matched(tags)
            if matching:
                return True
        return False

    def process_ignored(self, tags: Tags, processed: set[str]) -> None:
        """Mark all ignored tags as processed.

        :param tags: input tag dictionary
        :param processed: processed set
        """
        processed.update(
            {tag for tag in tags if self.is_no_drawable(tag, tags[tag])}
        )

    def get_shape_specification(
        self,
        structure: dict[str, Any],
        groups: dict[str, str] | None = None,
        color: Color | None = None,
    ) -> ShapeSpecification:
        """Parse shape specification from structure.

        The structure is just shape string identifier or dictionary with keys:
        shape (required), color (optional), and offset (optional).
        """
        color = color if color is not None else Color(self.variables["default"])
        offset: tuple[float, float] = (0.0, 0.0)
        flip_horizontally: bool = False
        flip_vertically: bool = False
        use_outline: bool = True

        shape_id: str = DEFAULT_SHAPE_ID
        if "shape" in structure:
            shape_id = structure["shape"]
            if groups:
                for key in groups:
                    shape_id = shape_id.replace(key, groups[key])
        else:
            logger.error("Invalid shape specification: `shape` key expected.")
        if "color" in structure:
            color = self.get_color(structure["color"])
        if "offset" in structure:
            offset = tuple(structure["offset"])
        if "flip_horizontally" in structure:
            flip_horizontally = structure["flip_horizontally"]
        if "flip_vertically" in structure:
            flip_vertically = structure["flip_vertically"]
        if "outline" in structure:
            use_outline = structure["outline"]

        return ShapeSpecification(
            shape_id,
            "main",
            offset,
            flip_horizontally,
            flip_vertically,
            use_outline,
            color,
        )
