"""
Simple OpenStreetMap renderer.

Author: Sergey Vartanov (me@enzet.ru).
"""
import os
import random
import sys
import yaml

import numpy as np

from roentgen import extract_icon
from roentgen import ui
from roentgen import svg
from roentgen.constructor import Constructor, get_path
from roentgen.flinger import GeoFlinger, Geo
from roentgen.osm_reader import OSMReader
from roentgen.osm_getter import get_osm
from roentgen.grid import draw_grid

from typing import List

ICONS_FILE_NAME: str = "icons/icons.svg"
TAGS_FILE_NAME: str = "data/tags.yml"
COLORS_FILE_NAME: str = "data/colors.yml"
MISSING_TAGS_FILE_NAME: str = "missing_tags.yml"


class Painter:

    def __init__(
            self, show_missing_tags, overlap, draw_nodes, mode, draw_captions,
            map_, flinger, output_file, icons, scheme):

        self.show_missing_tags = show_missing_tags
        self.overlap = overlap
        self.draw_nodes = draw_nodes
        self.mode = mode
        self.draw_captions = draw_captions

        self.map_ = map_
        self.flinger = flinger
        self.output_file = output_file
        self.icons = icons
        self.scheme = scheme

    def draw_raw_nodes(self):
        for node_id in self.map_.node_map:
            node = self.map_.node_map[node_id]
            flung = self.flinger.fling(node)
            self.output_file.circle(flung[0], flung[1], 0.2, color="FFFFFF")

    def no_draw(self, key):
        if key in self.scheme["tags_to_write"] or \
                key in self.scheme["tags_to_skip"]:
            return True
        for prefix in \
                self.scheme["prefix_to_write"] + self.scheme["prefix_to_skip"]:
            if key[:len(prefix) + 1] == prefix + ":":
                return True
        return False

    def to_write(self, key):
        if key in self.scheme["tags_to_skip"]:
            return False
        if key in self.scheme["tags_to_write"]:
            return True
        for prefix in self.scheme["prefix_to_write"]:
            if key[:len(prefix) + 1] == prefix + ":":
                return True
        return False

    def draw_shapes(self, shapes, points, x, y, fill, tags, processed):

        xxx = -(len(shapes) - 1) * 8

        if self.overlap != 0:
            for shape in shapes:
                has_space = True
                for p in points[-1000:]:
                    if x + xxx - self.overlap <= p[0] <= x + xxx + self.overlap and \
                            y - self.overlap <= p[1] <= y + self.overlap:
                        has_space = False
                        break
                if has_space:
                    self.draw_point_shape(shape, x + xxx, y, fill, tags=tags)
                    points.append([x + xxx, y])
                    xxx += 16
        else:
            for shape in shapes:
                self.draw_point_shape(shape, x + xxx, y, fill, tags=tags)
                xxx += 16

    def draw_texts(self, shapes, points, x, y, fill, tags, processed):

        if self.draw_captions == "no":
            return

        text_y: float = 0

        write_tags = self.construct_text(tags, processed)

        for text_struct in write_tags:
            fill = text_struct["fill"] if "fill" in text_struct else "444444"
            size = text_struct["size"] if "size" in text_struct else 10
            text_y += size + 1
            self.wr(text_struct["text"], x, y, fill, text_y, size=size)

        if self.show_missing_tags:
            for k in tags:
                if not self.no_draw(k) and k not in processed:
                    text = k + ": " + tags[k]
                    self.draw_text(text, x, float(y) + text_y + 18, "734A08")
                    text_y += 10

    def draw_text(self, text: str, x, y, fill, size=10, out_fill="FFFFFF",
                  out_opacity=1.0, out_fill_2=None, out_opacity_2=1.0):
        """
        Drawing text.

          ######     ###  outline 2
         #------#    ---  outline 1
        #| Text |#
         #------#
          ######
        """
        text = text.replace("&", "and")
        if out_fill_2:
            self.output_file.write(
                f'<text x="{x}" y="{y}" style="font-size:' +
                str(
                    size) + ";text-anchor:middle;font-family:Roboto;fill:#" +
                out_fill_2 + ";stroke-linejoin:round;stroke-width:5;stroke:#" +
                out_fill_2 + ";opacity:" + str(
                    out_opacity_2) + ';">' + text + "</text>")
        if out_fill:
            self.output_file.write(
                f'<text x="{x}" y="{y}" style="font-size:' +
                str(
                    size) + ";text-anchor:middle;font-family:Roboto;fill:#" +
                out_fill + ";stroke-linejoin:round;stroke-width:3;stroke:#" +
                out_fill + ";opacity:" + str(
                    out_opacity) + ';">' + text + "</text>")
        self.output_file.write(
            f'<text x="{x}" y="{y}" style="font-size:' +
            str(size) + ";text-anchor:middle;font-family:Roboto;fill:#" +
            fill + ';">' + text + "</text>")

    def wr(self, text, x, y, fill, text_y, size=10):
        text = text[:26] + ("..." if len(text) > 26 else "")
        self.draw_text(text, x, float(y) + text_y + 8, fill, size=size)

    def construct_text(self, tags, processed):
        for key in tags:
            tags[key] = tags[key].replace("&quot;", '"')
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
            texts.append({"text": name, "fill": "000000"})
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
            texts.append({"text": link, "fill": "000088"})
            tags.pop("website", None)
        for k in ["phone"]:
            if k in tags:
                texts.append({"text": tags[k], "fill": "444444"})
                tags.pop(k)
        for tag in tags:
            if self.to_write(tag) and not (tag in processed):
                # texts.append({"text": tag + ": " + tags[tag]})
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
                    shifted_1 = np.add(flung_1, shift_1)
                    shifted_2 = np.add(flung_2, shift_2)
                    self.output_file.write(
                        f'<path d="M '
                        f"{shifted_1[0]},{shifted_1[1]} L "
                        f"{shifted_1[0]},{shifted_1[1]} "
                        f"{shifted_2[0]},{shifted_2[1]} "
                        f'{shifted_2[0]},{shifted_2[1]} Z" '
                        f'style="fill:#{color};stroke:#{color};'
                        f'stroke-width:1;" />\n')
            elif way.path:
                # TODO: implement
                pass

    def draw(self, nodes, ways, points):

        ways = sorted(ways, key=lambda x: x.layer)
        for way in ways:
            if way.kind == "way":
                if way.nodes:
                    path = get_path(way.nodes, [0, 0], self.map_, self.flinger)
                    self.output_file.write(
                        f'<path d="{path}" style="' + way.style + '" />\n')
                else:
                    self.output_file.write(
                        f'<path d="{way.path}" style="' + way.style + '" />\n')

        # Building shade

        self.output_file.write('<g style="opacity:0.1;">\n')
        for way in ways:
            if way.kind == "building":
                if way.nodes:
                    shift = [-5, 5]
                    if way.levels:
                        shift = [-5 * way.levels, 5 * way.levels]
                    for i in range(len(way.nodes) - 1):
                        node_1 = self.map_.node_map[way.nodes[i]]
                        node_2 = self.map_.node_map[way.nodes[i + 1]]
                        flung_1 = self.flinger.fling(Geo(node_1.lat, node_1.lon))
                        flung_2 = self.flinger.fling(Geo(node_2.lat, node_2.lon))
                        self.output_file.write(
                            f'<path d="M '
                            f'{flung_1[0]},{flung_1[1]} L '
                            f"{flung_2[0]},{flung_2[1]} "
                            f"{flung_2[0] + shift[0]},{flung_2[1] + shift[1]} "
                            f'{flung_1[0] + shift[0]},{flung_1[1] + shift[1]} Z" '
                            f'style="fill:#000000;stroke:#000000;stroke-width:1;" />\n')
        self.output_file.write("</g>\n")

        # Building walls

        self.draw_building_walls(1, "AAAAAA", ways)
        self.draw_building_walls(2, "C3C3C3", ways)
        self.draw_building_walls(3, "DDDDDD", ways)

        # Building roof

        for way in ways:
            if way.kind == "building":
                if way.nodes:
                    shift = [0, -3]
                    if way.levels:
                        shift = [0 * way.levels, min(-3, -1 * way.levels)]
                    path = get_path(way.nodes, shift, self.map_, self.flinger)
                    self.output_file.write(
                        f'<path d="{path}" style="{way.style};opacity:1;" />\n')
                else:
                    self.output_file.write(
                        f'<path d="{way.path}" '
                        f'style="{way.style};opacity:1;" />\n')

        # Trees

        for node in nodes:
            if not("natural" in node.tags and
                   node.tags["natural"] == "tree" and
                   "diameter_crown" in node.tags):
                continue
            self.output_file.circle(
                float(node.x) + (random.random() - 0.5) * 10,
                float(node.y) + (random.random() - 0.5) * 10,
                float(node.tags["diameter_crown"]) * 1.2,
                color='688C44', fill='688C44', opacity=0.3)

        # All other nodes

        nodes = sorted(nodes, key=lambda x: x.layer)
        for node in nodes:
            if "natural" in node.tags and \
                   node.tags["natural"] == "tree" and \
                   "diameter_crown" in node.tags:
                continue
            self.draw_shapes(
                node.shapes, points, node.x, node.y, node.color, node.tags,
                node.processed)

        for node in nodes:
            if self.mode not in ["time", "user-coloring"]:
                self.draw_texts(
                    node.shapes, points, node.x, node.y, node.color,
                    node.tags, node.processed)

    def draw_point_shape(self, name, x, y, fill, tags=None):
        if not isinstance(name, list):
            name = [name]
        if self.mode not in ["time", "user-coloring"]:
            for one_name in name:
                shape, xx, yy, _ = self.icons.get_path(one_name)
                self.draw_point_outline(
                    shape, x, y, fill, mode=self.mode, size=16, xx=xx, yy=yy)
        for one_name in name:
            shape, xx, yy, _ = self.icons.get_path(one_name)
            self.draw_point(shape, x, y, fill, size=16, xx=xx, yy=yy, tags=tags)

    def draw_point(self, shape, x, y, fill, size=16, xx=0, yy=0, tags=None):
        x = int(float(x))
        y = int(float(y))
        self.output_file.write(
            '<path d="' + shape + '" style="fill:#' + fill +
            ';fill-opacity:1" transform="translate(' +
            str(x - size / 2.0 - xx * 16) + "," + str(
                y - size / 2.0 - yy * 16) +
            ')">')
        if tags:
            self.output_file.write("<title>")
            self.output_file.write(
                "\n".join(map(lambda x: x + ": " + tags[x], tags)))
            self.output_file.write("</title>")
        self.output_file.write("</path>\n")

    def draw_point_outline(self, shape, x, y, fill, mode="default", size=16, xx=0, yy=0):
        x = int(float(x))
        y = int(float(y))
        opacity = 0.5
        stroke_width = 2.2
        outline_fill = self.scheme["colors"]["outline_color"]
        if mode not in ["user-coloring", "time"]:
            r = int(fill[0:2], 16)
            g = int(fill[2:4], 16)
            b = int(fill[4:6], 16)
            Y = 0.2126 * r + 0.7152 * g + 0.0722 * b
            if Y > 200:
                outline_fill = "000000"
                opacity = 0.7
        self.output_file.write(
            '<path d="' + shape + '" style="fill:#' + outline_fill + ";opacity:" +
            str(opacity) + ";" + "stroke:#" + outline_fill +
            f';stroke-width:{stroke_width};stroke-linejoin:round;" ' + 'transform="translate(' +
            str(x - size / 2.0 - xx * 16) + "," + str(y - size / 2.0 - yy * 16) +
            ')" />\n')


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
    return True


def main():
    if len(sys.argv) == 2:
        if sys.argv[1] == "grid":
            draw_grid()
        return

    options = ui.parse_options(sys.argv)

    if not options:
        sys.exit(1)

    background_color = "EEEEEE"
    if options.mode in ["user-coloring", "time"]:
        background_color = "111111"

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

    if options.mode in ["user-coloring", "time"]:
        full = True

    osm_reader = OSMReader()

    for file_name in input_file_name:
        if not os.path.isfile(file_name):
            print("Fatal: no such file: " + file_name + ".")
            sys.exit(1)

        map_ = osm_reader.parse_osm_file(
            file_name, parse_ways=options.draw_ways,
            parse_relations=options.draw_ways, full=full)

    output_file = svg.SVG(open(options.output_file_name, "w+"))

    w, h = list(map(lambda x: float(x), options.size.split(",")))

    output_file.begin(w, h)
    output_file.write(
        "<title>Rӧntgen</title><style>path:hover {stroke: #FF0000;}</style>\n")
    output_file.rect(0, 0, w, h, color=background_color)

    min1 = Geo(boundary_box[1], boundary_box[0])
    max1 = Geo(boundary_box[3], boundary_box[2])

    authors = {}
    missing_tags = {}
    points = []

    scheme = yaml.load(open(TAGS_FILE_NAME), Loader=yaml.FullLoader)
    scheme["cache"] = {}
    w3c_colors = yaml.load(open(COLORS_FILE_NAME), Loader=yaml.FullLoader)
    for color_name in w3c_colors:
        scheme["colors"][color_name] = w3c_colors[color_name]

    flinger = GeoFlinger(min1, max1, [0, 0], [w, h])

    icons = extract_icon.IconExtractor(ICONS_FILE_NAME)

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
        map_=map_, flinger=flinger, output_file=output_file, icons=icons,
        scheme=scheme)
    painter.draw(constructor.nodes, constructor.ways, points)

    if flinger.space[0] == 0:
        output_file.rect(0, 0, w, flinger.space[1], color="FFFFFF")
        output_file.rect(
            0, h - flinger.space[1], w, flinger.space[1], color="FFFFFF")
    if flinger.space[1] == 0:
        output_file.rect(0, 0, flinger.space[0], h, color="FFFFFF")
        output_file.rect(
            w - flinger.space[0], 0, flinger.space[0], h, color="FFFFFF")

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
                output_file.text(
                    ((t1 + t2) * 0.5)[0], ((t1 + t2) * 0.5)[1] + 40,
                    str(int(matrix[i][j])), size=80, color="440000",
                    opacity=0.1, align="center")

    output_file.end()

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
