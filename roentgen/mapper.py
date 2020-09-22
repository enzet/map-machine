"""
Simple OpenStreetMap renderer.

Author: Sergey Vartanov (me@enzet.ru).
"""
import numpy as np
import os
import svgwrite
import sys

from colour import Color
from svgwrite.container import Group
from svgwrite.path import Path
from svgwrite.shapes import Rect
from svgwrite.text import Text
from typing import Any, Dict, List, Optional

from roentgen import ui
from roentgen.address import get_address
from roentgen.constructor import Constructor, Point, Figure, TextStruct, Building
from roentgen.flinger import Flinger
from roentgen.grid import draw_grid
from roentgen.extract_icon import Icon, IconExtractor
from roentgen.osm_getter import get_osm
from roentgen.osm_reader import Map, OSMReader
from roentgen.scheme import Scheme
from roentgen.direction import DirectionSet, Sector
from roentgen.util import MinMax
from roentgen.color import is_bright

ICONS_FILE_NAME: str = "icons/icons.svg"
TAGS_FILE_NAME: str = "data/tags.yml"
MISSING_TAGS_FILE_NAME: str = "missing_tags.yml"

AUTHOR_MODE = "user-coloring"
CREATION_TIME_MODE = "time"

DEFAULT_FONT = "Roboto"


class Painter:
    """
    Map drawing.
    """

    def __init__(
            self, show_missing_tags: bool, overlap: int, draw_nodes: bool,
            mode: str, draw_captions: str, map_: Map, flinger: Flinger,
            svg: svgwrite.Drawing, icon_extractor: IconExtractor,
            scheme: Scheme):

        self.show_missing_tags: bool = show_missing_tags
        self.overlap: int = overlap
        self.draw_nodes: bool = draw_nodes
        self.mode: str = mode
        self.draw_captions: str = draw_captions

        self.map_: Map = map_
        self.flinger: Flinger = flinger
        self.svg: svgwrite.Drawing = svg
        self.icon_extractor = icon_extractor
        self.scheme: Scheme = scheme

    def draw_shapes(self, node: Point, points: List[List[float]]):
        """
        Draw shapes for one node.
        """
        if node.icon_set.is_default and not node.is_for_node:
            return

        left: float = -(len(node.icon_set.icons) - 1) * 8

        if self.overlap != 0:
            for shape_ids in node.icon_set.icons:
                has_space = True
                for p in points[-1000:]:
                    if node.point[0] + left - self.overlap <= p[0] \
                            <= node.point[0] + left + self.overlap and \
                            node.point[1] - self.overlap <= p[1] \
                            <= node.point[1] + self.overlap:
                        has_space = False
                        break
                if has_space:
                    self.draw_point_shape(
                        shape_ids, (node.point[0] + left, node.point[1]),
                        node.icon_set.color, tags=node.tags)
                    points.append([node.point[0] + left, node.point[1]])
                    left += 16
        else:
            for shape_ids in node.icon_set.icons:
                self.draw_point_shape(
                    shape_ids, (node.point[0] + left, node.point[1]),
                    node.icon_set.color, tags=node.tags)
                left += 16

    def draw_texts(self, node: Point):
        """
        Draw all labels.
        """
        text_y: float = 0

        write_tags = self.construct_text(node.tags, node.icon_set.processed)

        for text_struct in write_tags:  # type: TextStruct
            text_y += text_struct.size + 1
            text = text_struct.text
            text = text.replace("&quot;", '"')
            text = text.replace("&amp;", '&')
            text = text[:26] + ("..." if len(text) > 26 else "")
            self.draw_text(
                text, (node.point[0], node.point[1] + text_y + 8),
                text_struct.fill, size=text_struct.size)

        if self.show_missing_tags:
            for tag in node.tags:  # type: str
                if not self.scheme.is_no_drawable(tag) and \
                        tag not in node.icon_set.processed:
                    text = f"{tag}: {node.tags[tag]}"
                    self.draw_text(
                        text, (node.point[0], node.point[1] + text_y + 18),
                        Color("#734A08"))
                    text_y += 10

    def draw_text(
            self, text: str, point, fill: Color, size: float = 10,
            out_fill=Color("white"), out_opacity=1.0,
            out_fill_2: Optional[Color] = None, out_opacity_2=1.0):
        """
        Drawing text.

          ######     ###  outline 2
         #------#    ---  outline 1
        #| Text |#
         #------#
          ######
        """
        if out_fill_2:
            self.svg.add(Text(
                text, point, font_size=size, text_anchor="middle",
                font_family=DEFAULT_FONT, fill=out_fill_2.hex,
                stroke_linejoin="round", stroke_width=5,
                stroke=out_fill_2.hex, opacity=out_opacity_2))
        if out_fill:
            self.svg.add(Text(
                text, point, font_size=size, text_anchor="middle",
                font_family=DEFAULT_FONT, fill=out_fill.hex,
                stroke_linejoin="round", stroke_width=3,
                stroke=out_fill.hex, opacity=out_opacity))
        self.svg.add(Text(
            text, point, font_size=size, text_anchor="middle",
            font_family=DEFAULT_FONT, fill=fill.hex))

    def construct_text(self, tags, processed):
        """
        Construct labels for not processed tags.
        """
        texts: List[TextStruct] = []

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
            alt_name += "бывш. " + tags["old_name"]

        address = get_address(tags, self.draw_captions)

        if name:
            texts.append(TextStruct(name, Color("black")))
        if alt_name:
            texts.append(TextStruct("(" + alt_name + ")"))
        if address:
            texts.append(TextStruct(", ".join(address)))

        if self.draw_captions == "main":
            return texts

        if "route_ref" in tags:
            texts.append(TextStruct(tags["route_ref"].replace(";", " ")))
            tags.pop("route_ref", None)
        if "cladr:code" in tags:
            texts.append(TextStruct(tags["cladr:code"], size=7))
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
            texts.append(TextStruct(link, Color("#000088")))
            tags.pop("website", None)
        for k in ["phone"]:
            if k in tags:
                texts.append(TextStruct(tags[k], Color("#444444")))
                tags.pop(k)
        for tag in tags:
            if self.scheme.is_writable(tag) and not (tag in processed):
                texts.append(TextStruct(tags[tag]))
        return texts

    def draw_building_walls(self, stage, color: Color, ways):
        """
        Draw area between way and way shifted by the vector.
        """
        for way in ways:  # type: Building
            if stage == 1:
                shift_1 = [0, 0]
                shift_2 = [0, -1]
            elif stage == 2:
                shift_1 = [0, -1]
                shift_2 = [0, -2]
            else:
                shift_1 = [0, -2]
                shift_2 = [0, min(-3, -1 * way.get_levels())]

            for nodes in way.inners + way.outers:
                for i in range(len(nodes) - 1):
                    flung_1 = self.flinger.fling(nodes[i].position)
                    flung_2 = self.flinger.fling(nodes[i + 1].position)

                    self.svg.add(self.svg.path(
                        d=("M", np.add(flung_1, shift_1), "L",
                           np.add(flung_2, shift_1), np.add(flung_2, shift_2),
                           np.add(flung_1, shift_2), "Z"),
                        fill=color.hex, stroke="#CCCCCC", stroke_width=1))

    def draw(self, constructor: Constructor, points):
        """
        Draw map.
        """
        ways = sorted(constructor.figures, key=lambda x: x.layer)
        ways_length: int = len(ways)
        for index, way in enumerate(ways):  # type: Figure
            ui.progress_bar(index, ways_length, step=10, text="Drawing ways")
            path: str = way.get_path(self.flinger)
            if path:
                p = Path(d=path)
                p.update(way.style)
                self.svg.add(p)
        ui.progress_bar(-1, 0, text="Drawing ways")

        # Building shade

        building_shade = Group(opacity=0.1)

        for way in constructor.buildings:  # type: Building
            shift = [-5, 5]
            shift = [-5 * way.get_levels(), 5 * way.get_levels()]
            for nodes11 in way.inners + way.outers:
                for i in range(len(nodes11) - 1):
                    flung_1 = self.flinger.fling(nodes11[i].position)
                    flung_2 = self.flinger.fling(nodes11[i + 1].position)
                    building_shade.add(Path(
                        ("M", flung_1, "L", flung_2, np.add(flung_2, shift),
                         np.add(flung_1, shift), "Z"),
                        fill="#000000", stroke="#000000", stroke_width=1))

        self.svg.add(building_shade)

        # Building walls

        self.draw_building_walls(1, Color("#AAAAAA"), constructor.buildings)
        self.draw_building_walls(2, Color("#C3C3C3"), constructor.buildings)
        self.draw_building_walls(3, Color("#DDDDDD"), constructor.buildings)

        # Building roof

        def sort_by_levels(building: Building):
            return building.get_levels()

        for way in sorted(constructor.buildings, key=sort_by_levels):  # type: Building
            shift = [0, -3]
            shift = np.array([
                0 * way.get_levels(), min(-3, -1 * way.get_levels())])
            path: str = way.get_path(self.flinger, shift)
            if path:
                p = Path(d=path, opacity=1)
                p.update(way.style)
                self.svg.add(p)

        # Trees

        for node in constructor.nodes:
            if not (node.get_tag("natural") == "tree" and
                    ("diameter_crown" in node.tags or
                     "circumference" in node.tags)):
                continue
            if "circumference" in node.tags:
                self.svg.add(self.svg.circle(
                    node.point,
                    float(node.tags["circumference"]) *
                    self.flinger.get_scale(node.coordinates) / 2,
                    fill="#AAAA88", opacity=0.3))
            if "diameter_crown" in node.tags:
                self.svg.add(self.svg.circle(
                    node.point,
                    float(node.tags["diameter_crown"]) *
                    self.flinger.get_scale(node.coordinates) / 2,
                    fill=self.scheme.get_color("evergreen"), opacity=0.3))

        # Directions

        for node in constructor.nodes:  # type: Point

            angle = None
            is_revert_gradient: bool = False

            if node.get_tag("man_made") == "surveillance":
                direction = node.get_tag("camera:direction")
                if "camera:angle" in node.tags:
                    angle = float(node.get_tag("camera:angle"))
                if "angle" in node.tags:
                    angle = float(node.get_tag("angle"))
                direction_radius: float = \
                    25 * self.flinger.get_scale(node.coordinates)
                direction_color: Color = \
                    self.scheme.get_color("direction_camera_color")
            elif node.get_tag("traffic_sign") == "stop":
                direction = node.get_tag("direction")
                direction_radius: float = \
                    25 * self.flinger.get_scale(node.coordinates)
                direction_color: Color = Color("red")
            else:
                direction = node.get_tag("direction")
                direction_radius: float = \
                    50 * self.flinger.get_scale(node.coordinates)
                direction_color: Color = \
                    self.scheme.get_color("direction_view_color")
                is_revert_gradient = True

            if not direction:
                continue

            point = (node.point.astype(int)).astype(float)

            if angle:
                paths = [Sector(direction, angle).draw(point, direction_radius)]
            else:
                paths = DirectionSet(direction).draw(point, direction_radius)

            for path in paths:
                gradient = self.svg.defs.add(self.svg.radialGradient(
                    center=point, r=direction_radius,
                    gradientUnits="userSpaceOnUse"))
                if is_revert_gradient:
                    gradient \
                        .add_stop_color(0, direction_color.hex, opacity=0) \
                        .add_stop_color(1, direction_color.hex, opacity=0.7)
                else:
                    gradient \
                        .add_stop_color(0, direction_color.hex, opacity=0.4) \
                        .add_stop_color(1, direction_color.hex, opacity=0)
                self.svg.add(self.svg.path(
                    d=["M", point] + path + ["L", point, "Z"],
                    fill=gradient.get_paint_server()))

        # All other nodes

        nodes = sorted(constructor.nodes, key=lambda x: x.layer)
        for index, node in enumerate(nodes):  # type: int, Point
            if node.get_tag("natural") == "tree" and \
                    ("diameter_crown" in node.tags or
                     "circumference" in node.tags):
                continue
            ui.progress_bar(index, len(nodes), step=10, text="Drawing nodes")
            self.draw_shapes(node, points)
        ui.progress_bar(-1, len(nodes), step=10, text="Drawing nodes")

        if self.draw_captions == "no":
            return

        for node in nodes:  # type: Point
            if self.mode not in [CREATION_TIME_MODE, AUTHOR_MODE]:
                self.draw_texts(node)

    def draw_point_shape(
            self, shape_ids: List[str], point, fill: Color, tags=None):
        """
        Draw one icon.
        """
        if self.mode not in [CREATION_TIME_MODE, AUTHOR_MODE]:
            for shape_id in shape_ids:  # type: str
                icon, _ = self.icon_extractor.get_path(shape_id)
                self.draw_point_outline(icon, point, fill, mode=self.mode)
        for shape_id in shape_ids:  # type: str
            icon, _ = self.icon_extractor.get_path(shape_id)
            self.draw_point(icon, point, fill, tags=tags)

    def draw_point(
            self, icon: Icon, point: (float, float), fill: Color,
            tags: Dict[str, str] = None) -> None:

        point = np.array(list(map(lambda x: int(x), point)))
        title: str = "\n".join(map(lambda x: x + ": " + tags[x], tags))

        path: svgwrite.path.Path = icon.get_path(self.svg, point)
        path.update({"fill": fill.hex})
        path.set_desc(title=title)
        self.svg.add(path)

    def draw_point_outline(
            self, icon: Icon, point, fill: Color, mode="default"):

        point = np.array(list(map(lambda x: int(x), point)))

        opacity: float = 0.5
        stroke_width: float = 2.2
        outline_fill: Color = self.scheme.get_color("outline_color")

        if mode not in [AUTHOR_MODE, CREATION_TIME_MODE] and is_bright(fill):
            outline_fill = Color("black")
            opacity = 0.7

        path = icon.get_path(self.svg, point)
        path.update({
            "fill": outline_fill.hex, "opacity": opacity,
            "stroke": outline_fill.hex, "stroke-width": stroke_width,
            "stroke-linejoin": "round"})
        self.svg.add(path)


def check_level_number(tags: Dict[str, Any], level: float):
    """
    Check if element described by tags is no the specified level.
    """
    if "level" in tags:
        levels = map(float, tags["level"].replace(",", ".").split(";"))
        if level not in levels:
            return False
    else:
        return False
    return True


def check_level_overground(tags: Dict[str, Any]):
    """
    Check if element described by tags is overground.
    """
    if "level" in tags:
        try:
            levels = map(float, tags["level"].replace(",", ".").split(";"))
            for level in levels:
                if level <= 0:
                    return False
        except ValueError:
            pass
    if "layer" in tags:
        try:
            levels = map(float, tags["layer"].replace(",", ".").split(";"))
            for level in levels:
                if level <= 0:
                    return False
        except ValueError:
            pass
    if "parking" in tags and tags["parking"] == "underground":
        return False
    return True


def main(argv):
    if len(argv) == 2:
        if argv[1] == "grid":
            draw_grid()
        return

    options = ui.parse_options(argv)

    if not options:
        sys.exit(1)

    background_color: Color = Color("#EEEEEE")
    if options.mode in [AUTHOR_MODE, CREATION_TIME_MODE]:
        background_color: Color = Color("#111111")

    if options.input_file_name:
        input_file_name = options.input_file_name
    else:
        content = get_osm(options.boundary_box)
        if not content:
            ui.error("cannot download OSM data")
        input_file_name = [os.path.join("map", options.boundary_box + ".osm")]

    boundary_box = list(map(
        lambda x: float(x.replace('m', '-')), options.boundary_box.split(',')))

    full = False  # Full keys getting

    if options.mode in [AUTHOR_MODE, CREATION_TIME_MODE]:
        full = True

    osm_reader = OSMReader()

    for file_name in input_file_name:
        if not os.path.isfile(file_name):
            print("Fatal: no such file: " + file_name + ".")
            sys.exit(1)

        osm_reader.parse_osm_file(
            file_name, parse_ways=options.draw_ways,
            parse_relations=options.draw_ways, full=full)

    map_: Map = osm_reader.map_

    missing_tags = {}
    points = []

    scheme: Scheme = Scheme(TAGS_FILE_NAME)

    min1: np.array = np.array((boundary_box[1], boundary_box[0]))
    max1: np.array = np.array((boundary_box[3], boundary_box[2]))
    flinger: Flinger = Flinger(MinMax(min1, max1), options.scale)
    size: np.array = flinger.size

    svg: svgwrite.Drawing = \
        svgwrite.Drawing(options.output_file_name, size=size)
    svg.add(Rect((0, 0), size, fill=background_color))

    icon_extractor: IconExtractor = IconExtractor(ICONS_FILE_NAME)

    def check_level(x):
        """ Draw objects on all levels. """
        return True

    if options.level:
        if options.level == "overground":
            check_level = check_level_overground
        elif options.level == "underground":
            def check_level(x):
                """ Draw underground objects. """
                return not check_level_overground(x)
        else:
            def check_level(x):
                """ Draw objects on the specified level. """
                return not check_level_number(x, float(options.level))

    constructor: Constructor = Constructor(
        check_level, options.mode, options.seed, map_, flinger, scheme)
    if options.draw_ways:
        constructor.construct_ways()
        constructor.construct_relations()
    constructor.construct_nodes()

    painter: Painter = Painter(
        show_missing_tags=options.show_missing_tags, overlap=options.overlap,
        draw_nodes=options.draw_nodes, mode=options.mode,
        draw_captions=options.draw_captions,
        map_=map_, flinger=flinger, svg=svg, icon_extractor=icon_extractor,
        scheme=scheme)
    painter.draw(constructor, points)

    if options.show_index:
        draw_index(flinger, map_, max1, min1, svg)

    print("Writing output SVG...")
    svg.write(open(options.output_file_name, "w"))
    print("Done.")

    top_missing_tags = \
        sorted(missing_tags.keys(), key=lambda x: -missing_tags[x])
    missing_tags_file = open(MISSING_TAGS_FILE_NAME, "w+")
    for tag in top_missing_tags:
        missing_tags_file.write(
            f'- {{tag: "{tag}", count: {missing_tags[tag]}}}\n')
    missing_tags_file.close()


def draw_index(flinger, map_, max1, min1, svg):
    print(min1[1], max1[1])
    print(min1[0], max1[0])
    lon_step = 0.001
    lat_step = 0.001
    matrix = []
    lat_number = int((max1[0] - min1[0]) / lat_step) + 1
    lon_number = int((max1[1] - min1[1]) / lon_step) + 1
    for i in range(lat_number):
        row = []
        for j in range(lon_number):
            row.append(0)
        matrix.append(row)
    for node_id in map_.node_map:  # type: int
        node = map_.node_map[node_id]
        i = int((node[0] - min1[0]) / lat_step)
        j = int((node[1] - min1[1]) / lon_step)
        if (0 <= i < lat_number) and (0 <= j < lon_number):
            matrix[i][j] += 1
            if "tags" in node:
                matrix[i][j] += len(node.nodes)
    for way_id in map_.way_map:  # type: int
        way = map_.way_map[way_id]
        if "tags" in way:
            for node_id in way.nodes:
                node = map_.node_map[node_id]
                i = int((node[0] - min1[0]) / lat_step)
                j = int((node[1] - min1[1]) / lon_step)
                if (0 <= i < lat_number) and (0 <= j < lon_number):
                    matrix[i][j] += len(way.nodes) / float(
                        len(way.nodes))
    for i in range(lat_number):
        for j in range(lon_number):
            t1 = flinger.fling(np.array((
                min1[0] + i * lat_step, min1[1] + j * lon_step)))
            t2 = flinger.fling(np.array((
                min1[0] + (i + 1) * lat_step,
                min1[1] + (j + 1) * lon_step)))
            svg.add(Text(
                str(int(matrix[i][j])),
                (((t1 + t2) * 0.5)[0], ((t1 + t2) * 0.5)[1] + 40),
                font_size=80, fill="440000",
                opacity=0.1, align="center"))
