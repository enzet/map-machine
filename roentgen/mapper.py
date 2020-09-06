"""
Simple OpenStreetMap renderer.

Author: Sergey Vartanov (me@enzet.ru).
"""
import numpy as np
import os
import svgwrite
import sys

from svgwrite.container import Group
from svgwrite.path import Path
from svgwrite.shapes import Circle, Rect
from svgwrite.text import Text
from typing import Dict, List

from roentgen import ui
from roentgen.constructor import Constructor, get_path, Node, Way
from roentgen.flinger import GeoFlinger, Geo
from roentgen.grid import draw_grid
from roentgen.extract_icon import Icon, IconExtractor
from roentgen.osm_getter import get_osm
from roentgen.osm_reader import Map, OSMReader
from roentgen.scheme import Scheme
from roentgen.direction import DirectionSet

ICONS_FILE_NAME: str = "icons/icons.svg"
TAGS_FILE_NAME: str = "data/tags.yml"
COLORS_FILE_NAME: str = "data/colors.yml"
MISSING_TAGS_FILE_NAME: str = "missing_tags.yml"

AUTHOR_MODE = "user-coloring"
CREATION_TIME_MODE = "time"


class Painter:
    """
    Map drawing.
    """
    def __init__(
            self, show_missing_tags: bool, overlap: int, draw_nodes: bool,
            mode: str, draw_captions: bool, map_: Map, flinger: GeoFlinger,
            svg: svgwrite.Drawing, icon_extractor: IconExtractor,
            scheme: Scheme):

        self.show_missing_tags: bool = show_missing_tags
        self.overlap: int = overlap
        self.draw_nodes: bool = draw_nodes
        self.mode: str = mode
        self.draw_captions = draw_captions

        self.map_: Map = map_
        self.flinger: GeoFlinger = flinger
        self.svg: svgwrite.Drawing = svg
        self.icon_extractor = icon_extractor
        self.scheme: Scheme = scheme

    def draw_shapes(self, node: Node, points: List[List[float]]):
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

    def draw_texts(self, node: Node):
        """
        Draw all labels.
        """
        text_y: float = 0

        write_tags = self.construct_text(node.tags, node.icon_set.processed)

        for text_struct in write_tags:
            fill = text_struct["fill"] if "fill" in text_struct else "#444444"
            size = text_struct["size"] if "size" in text_struct else 10
            text_y += size + 1
            text = text_struct["text"]
            text = text.replace("&quot;", '"')
            text = text.replace("&amp;", '&')
            text = text[:26] + ("..." if len(text) > 26 else "")
            self.draw_text(
                text, (node.point[0], node.point[1] + text_y + 8),
                fill, size=size)

        if self.show_missing_tags:
            for tag in node.tags:  # type: str
                if not self.scheme.is_no_drawable(tag) and \
                        tag not in node.icon_set.processed:
                    text = f"{tag}: {node.tags[tag]}"
                    self.draw_text(
                        text, (node.point[0], node.point[1] + text_y + 18),
                        "#734A08")
                    text_y += 10

    def draw_text(
            self, text: str, point, fill, size=10, out_fill="#FFFFFF",
            out_opacity=1.0, out_fill_2=None, out_opacity_2=1.0):
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
                font_family="Roboto", fill=out_fill_2,
                stroke_linejoin="round", stroke_width=5,
                stroke=out_fill_2, opacity=out_opacity_2))
        if out_fill:
            self.svg.add(Text(
                text, point, font_size=size, text_anchor="middle",
                font_family="Roboto", fill=out_fill,
                stroke_linejoin="round", stroke_width=3,
                stroke=out_fill, opacity=out_opacity))
        self.svg.add(Text(
            text, point, font_size=size, text_anchor="middle",
            font_family="Roboto", fill=fill))

    def construct_text(self, tags, processed):
        """
        Construct labels for not processed tags.
        """
        texts = []
        address: List[str] = []
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
        if "addr:postcode" in tags and self.draw_captions != "main":
            address.append(tags["addr:postcode"])
            tags.pop("addr:postcode", None)
        if "addr:country" in tags and self.draw_captions != "main":
            address.append(tags["addr:country"])
            tags.pop("addr:country", None)
        if "addr:city" in tags and self.draw_captions != "main":
            address.append(tags["addr:city"])
            tags.pop("addr:city", None)
        if "addr:street" in tags and self.draw_captions != "main":
            street = tags["addr:street"]
            if street.startswith("улица "):
                street = "ул. " + street[len("улица "):]
            address.append(street)
            tags.pop("addr:street", None)
        if "addr:housenumber" in tags:
            address.append(tags["addr:housenumber"])
            tags.pop("addr:housenumber", None)
        if name:
            texts.append({"text": name, "fill": "#000000"})
        if alt_name:
            texts.append({"text": "(" + alt_name + ")"})
        if address:
            texts.append({"text": ", ".join(address)})

        if self.draw_captions == "main":
            return texts

        if "route_ref" in tags:
            texts.append({"text": tags["route_ref"].replace(";", " ")})
            tags.pop("route_ref", None)
        if "cladr:code" in tags:
            texts.append({"text": tags["cladr:code"], "size": 7})
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
            texts.append({"text": link, "fill": "#000088"})
            tags.pop("website", None)
        for k in ["phone"]:
            if k in tags:
                texts.append({"text": tags[k], "fill": "#444444"})
                tags.pop(k)
        for tag in tags:
            if self.scheme.is_writable(tag) and not (tag in processed):
                texts.append({"text": tags[tag]})
        return texts

    def draw_building_walls(self, stage, color, ways):
        """
        Draw area between way and way shifted by the vector.
        """
        for way in ways:
            if way.kind != "building":
                continue

            if stage == 1:
                shift_1 = [0, 0]
                shift_2 = [0, -1]
            elif stage == 2:
                shift_1 = [0, -1]
                shift_2 = [0, -2]
            else:
                shift_1 = [0, -2]
                if way.levels:
                    shift_2 = [0, min(-3, -1 * way.levels)]
                else:
                    shift_2 = [0, -3]

            if way.nodes:
                for i in range(len(way.nodes) - 1):
                    node_1 = self.map_.node_map[way.nodes[i]]
                    node_2 = self.map_.node_map[way.nodes[i + 1]]
                    flung_1 = self.flinger.fling(Geo(node_1.lat, node_1.lon))
                    flung_2 = self.flinger.fling(Geo(node_2.lat, node_2.lon))

                    self.svg.add(self.svg.path(
                        d=("M", np.add(flung_1, shift_1), "L",
                           np.add(flung_2, shift_1), np.add(flung_2, shift_2),
                           np.add(flung_1, shift_2), "Z"),
                        fill=color, stroke=color, stroke_width=1))
            elif way.path:
                # TODO: implement
                pass

    def draw(self, nodes, ways, points):
        """
        Draw map.
        """
        ways = sorted(ways, key=lambda x: x.layer)
        for way in ways:
            if way.kind == "way":
                if way.nodes:
                    path = get_path(way.nodes, [0, 0], self.map_, self.flinger)
                    p = Path(d=path)
                    p.update(way.style)
                    self.svg.add(p)
                else:
                    p = Path(d=way.path)
                    p.update(way.style)
                    self.svg.add(p)

        # Building shade

        building_shade = Group(opacity=0.1)

        for way in ways:  # type: Way
            if way.kind != "building" or not way.nodes:
                continue
            shift = [-5, 5]
            if way.levels:
                shift = [-5 * way.levels, 5 * way.levels]
            for i in range(len(way.nodes) - 1):
                node_1 = self.map_.node_map[way.nodes[i]]
                node_2 = self.map_.node_map[way.nodes[i + 1]]
                flung_1 = self.flinger.fling(Geo(node_1.lat, node_1.lon))
                flung_2 = self.flinger.fling(Geo(node_2.lat, node_2.lon))
                building_shade.add(Path(
                    ("M", flung_1, "L", flung_2, np.add(flung_2, shift),
                     np.add(flung_1, shift), "Z"),
                    fill="#000000", stroke="#000000", stroke_width=1))

        self.svg.add(building_shade)

        # Building walls

        self.draw_building_walls(1, "#AAAAAA", ways)
        self.draw_building_walls(2, "#C3C3C3", ways)
        self.draw_building_walls(3, "#DDDDDD", ways)

        # Building roof

        for way in ways:  # type: Way
            if way.kind != "building":
                continue
            if way.nodes:
                shift = [0, -3]
                if way.levels:
                    shift = [0 * way.levels, min(-3, -1 * way.levels)]
                path = get_path(way.nodes, shift, self.map_, self.flinger)
                p = Path(d=path, opacity=1)
                p.update(way.style)
                self.svg.add(p)
            else:
                p = Path(d=way.path, opacity=1)
                p.update(way.style)
                self.svg.add(p)

        # Trees

        for node in nodes:
            if not("natural" in node.tags and
                   node.tags["natural"] == "tree" and
                   "diameter_crown" in node.tags):
                continue
            self.svg.add(Circle(
                node.point, float(node.tags["diameter_crown"]) * 1.2,
                fill="#688C44", stroke="#688C44", opacity=0.3))

        # Directions

        for node in nodes:
            if not ("tourism" in node.tags and
                    node.tags["tourism"] == "viewpoint" and
                    "direction" in node.tags):
                continue

            DIRECTION_RADIUS: int = 50
            DIRECTION_COLOR: str = self.scheme.get_color("direction_color")

            for path in DirectionSet(node.tags["direction"])\
                    .draw(node.point, DIRECTION_RADIUS):
                gradient = self.svg.defs.add(self.svg.radialGradient(
                    center=node.point, r=DIRECTION_RADIUS,
                    gradientUnits="userSpaceOnUse"))
                gradient\
                    .add_stop_color(0, DIRECTION_COLOR, opacity=0)\
                    .add_stop_color(1, DIRECTION_COLOR, opacity=0.7)
                self.svg.add(self.svg.path(
                    d=["M", node.point] + path + ["L", node.point, "Z"],
                    fill=gradient.get_paint_server()))

        # All other nodes

        nodes = sorted(nodes, key=lambda x: x.layer)
        for node in nodes:  # type: Node
            if "natural" in node.tags and \
                   node.tags["natural"] == "tree" and \
                   "diameter_crown" in node.tags:
                continue
            self.draw_shapes(node, points)

        if self.draw_captions == "no":
            return

        for node in nodes:  # type: Node
            if self.mode not in [CREATION_TIME_MODE, AUTHOR_MODE]:
                self.draw_texts(node)

    def draw_point_shape(self, shape_ids: List[str], point, fill, tags=None):
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
            self, icon: Icon, point: (float, float), fill: str,
            tags: Dict[str, str] = None) -> None:

        point = np.array(list(map(lambda x: int(x), point)))
        title: str = "\n".join(map(lambda x: x + ": " + tags[x], tags))

        path = icon.get_path(self.svg, point)
        path.update({"fill": fill})
        path.set_desc(title=title)
        self.svg.add(path)

    def draw_point_outline(
            self, icon: Icon, point, fill, mode="default"):

        point = np.array(list(map(lambda x: int(x), point)))

        opacity = 0.5
        stroke_width = 2.2
        outline_fill = self.scheme.get_color("outline_color")
        if mode not in [AUTHOR_MODE, CREATION_TIME_MODE]:
            r = int(fill[1:3], 16)
            g = int(fill[3:5], 16)
            b = int(fill[5:7], 16)
            Y = 0.2126 * r + 0.7152 * g + 0.0722 * b
            if Y > 200:
                outline_fill = "#000000"
                opacity = 0.7

        path = icon.get_path(self.svg, point)
        path.update({
            "fill": outline_fill, "opacity": opacity,
            "stroke": outline_fill, "stroke-width": stroke_width,
            "stroke-linejoin": "round"})
        self.svg.add(path)


def check_level_number(tags, level):
    if "level" in tags:
        levels = \
            map(lambda x: float(x), tags["level"].replace(",", ".").split(";"))
        if level not in levels:
            return False
    else:
        return False
    return True


def check_level_overground(tags):
    if "level" in tags:
        levels = \
            map(lambda x: float(x), tags["level"].replace(",", ".").split(";"))
        for level in levels:
            if level <= 0:
                return False
    if "layer" in tags:
        levels = \
            map(lambda x: float(x), tags["layer"].replace(",", ".").split(";"))
        for level in levels:
            if level <= 0:
                return False
    if "parking" in tags and tags["parking"] == "underground":
        return False
    return True


def main():
    if len(sys.argv) == 2:
        if sys.argv[1] == "grid":
            draw_grid()
        return

    options = ui.parse_options(sys.argv)

    if not options:
        sys.exit(1)

    background_color = "#EEEEEE"
    if options.mode in [AUTHOR_MODE, CREATION_TIME_MODE]:
        background_color = "#111111"

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

    w, h = list(map(lambda x: float(x), options.size.split(",")))

    svg: svgwrite.Drawing = \
        svgwrite.Drawing(options.output_file_name, size=(w, h))

    svg.add(Rect((0, 0), (w, h), fill=background_color))

    min1 = Geo(boundary_box[1], boundary_box[0])
    max1 = Geo(boundary_box[3], boundary_box[2])

    authors = {}
    missing_tags = {}
    points = []

    scheme = Scheme(TAGS_FILE_NAME, COLORS_FILE_NAME)

    flinger = GeoFlinger(min1, max1, [0, 0], [w, h])

    icon_extractor = IconExtractor(ICONS_FILE_NAME)

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

    constructor = Constructor(
        check_level, options.mode, options.seed, map_, flinger, scheme)
    if options.draw_ways:
        constructor.construct_ways()
        constructor.construct_relations()
    constructor.construct_nodes()

    painter = Painter(
        show_missing_tags=options.show_missing_tags, overlap=options.overlap,
        draw_nodes=options.draw_nodes, mode=options.mode,
        draw_captions=options.draw_captions,
        map_=map_, flinger=flinger, svg=svg, icon_extractor=icon_extractor,
        scheme=scheme)
    painter.draw(constructor.nodes, constructor.ways, points)

    if flinger.space[0] == 0:
        svg.add(Rect((0, 0), (w, flinger.space[1]), fill="#FFFFFF"))
        svg.add(Rect(
            (0, h - flinger.space[1]), (w, flinger.space[1]), fill="#FFFFFF"))
    if flinger.space[1] == 0:
        svg.add(Rect((0, 0), (flinger.space[0], h), fill="#FFFFFF"))
        svg.add(Rect(
            (w - flinger.space[0], 0), (flinger.space[0], h), fill="#FFFFFF"))

    if options.show_index:
        print(min1.lon, max1.lon)
        print(min1.lat, max1.lat)

        lon_step = 0.001
        lat_step = 0.001

        matrix = []

        lat_number = int((max1.lat - min1.lat) / lat_step) + 1
        lon_number = int((max1.lon - min1.lon) / lon_step) + 1

        for i in range(lat_number):
            row = []
            for j in range(lon_number):
                row.append(0)
            matrix.append(row)

        for node_id in map_.node_map:
            node = map_.node_map[node_id]
            i = int((node.lat - min1.lat) / lat_step)
            j = int((node.lon - min1.lon) / lon_step)
            if (0 <= i < lat_number) and (0 <= j < lon_number):
                matrix[i][j] += 1
                if "tags" in node:
                    matrix[i][j] += len(node.tags)

        for way_id in map_.way_map:
            way = map_.way_map[way_id]
            if "tags" in way:
                for node_id in way.nodes:
                    node = map_.node_map[node_id]
                    i = int((node.lat - min1.lat) / lat_step)
                    j = int((node.lon - min1.lon) / lon_step)
                    if (0 <= i < lat_number) and (0 <= j < lon_number):
                        matrix[i][j] += len(way.tags) / float(
                            len(way.nodes))

        for i in range(lat_number):
            for j in range(lon_number):
                t1 = flinger.fling(Geo(
                    min1.lat + i * lat_step, min1.lon + j * lon_step))
                t2 = flinger.fling(Geo(
                    min1.lat + (i + 1) * lat_step,
                    min1.lon + (j + 1) * lon_step))
                svg.add(Text(
                    str(int(matrix[i][j])),
                    (((t1 + t2) * 0.5)[0], ((t1 + t2) * 0.5)[1] + 40),
                    font_size=80, fill="440000",
                    opacity=0.1, align="center"))

    svg.write(open(options.output_file_name, "w"))

    top_missing_tags = \
        sorted(missing_tags.keys(), key=lambda x: -missing_tags[x])
    missing_tags_file = open(MISSING_TAGS_FILE_NAME, "w+")
    for tag in top_missing_tags:
        missing_tags_file.write(
            f'- {{tag: "{tag}", count: {missing_tags[tag]}}}\n')
    missing_tags_file.close()

    top_authors = sorted(authors.keys(), key=lambda x: -authors[x])
    for author in top_authors:
        print(f"{author}: {authors[author]}")
