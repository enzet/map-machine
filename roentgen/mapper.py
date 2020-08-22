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
from roentgen import process
from roentgen import ui
from roentgen import svg
from roentgen.flinger import GeoFlinger, Geo
from roentgen.osm_reader import OSMReader, OSMWay

from datetime import datetime
from typing import List, Optional, Set


outline_color = "FFFFFF"
beach_color = "F0E0C0"
building_color = "F8F0E8"  # "D0D0C0"
building_border_color = "DDDDDD"  # "AAAAAA"
construction_color = "CCCCCC"
cycle_color = "4444EE"
desert_color = "F0E0D0"
foot_color = "B89A74"
indoor_color = "E8E4E0"
indoor_border_color = "C0B8B0"
foot_border_color = "FFFFFF"
grass_color = "CFE0A8"
grass_border_color = "BFD098"
guide_strips_color = "228833"
parking_color = "DDCC99"
platform_color = "CCCCCC"
platform_border_color = "AAAAAA"
playground_color = "884400"
primary_border_color = "888888"  # "AA8800"
primary_color = "FFFFFF"  # "FFDD66"
private_access_color = "884444"
road_border_color = "CCCCCC"
sand_color = "F0E0D0"
water_color = "AACCFF"
water_border_color = "6688BB"
wood_color = "B8CC84"
wood_border_color = "A8BC74"

icons_file_name = "icons/icons.svg"
tags_file_name = "data/tags.yml"
colors_file_name = "data/colors.yml"
missed_tags_file_name = "missed_tags.yml"


class Node:
    def __init__(self, shapes, tags, x, y, color, path, processed, priority=0):
        self.shapes = shapes
        self.tags = tags
        self.x = x
        self.y = y
        self.color = color
        self.path = path
        self.processed = processed
        self.priority = priority
        self.layer = 0


class Way:
    def __init__(
            self, kind, nodes, path, style, layer=0.0, priority=0, levels=None):
        self.kind = kind
        self.nodes = nodes
        self.path = path
        self.style = style
        self.layer = layer
        self.priority = priority
        self.levels = levels


def get_path(nodes, shift, map_, flinger: GeoFlinger):
    path = ""
    prev_node = None
    for node_id in nodes:
        node = map_.node_map[node_id]
        flinged1 = np.add(flinger.fling(Geo(node.lat, node.lon)), shift)
        if prev_node:
            path += f"L {flinged1[0]},{flinged1[1]} "
        else:
            path += f"M {flinged1[0]},{flinged1[1]} "
        prev_node = map_.node_map[node_id]
    if nodes[0] == nodes[-1]:
        path += "Z"
    return path


def line_center(nodes, flinger: GeoFlinger):
    ma = [0, 0]
    mi = [10000, 10000]
    for node in nodes:
        flinged = flinger.fling(Geo(node.lat, node.lon))
        if flinged[0] > ma[0]: ma[0] = flinged[0]
        if flinged[1] > ma[1]: ma[1] = flinged[1]
        if flinged[0] < mi[0]: mi[0] = flinged[0]
        if flinged[1] < mi[1]: mi[1] = flinged[1]
    return [(ma[0] + mi[0]) / 2.0, (ma[1] + mi[1]) / 2.0]


def get_float(string):
    try:
        return float(string)
    except ValueError:
        return 0


def get_user_color(user, seed):
    if user == "":
        return "000000"
    rgb = hex(abs(hash(seed + user)))[-6:]
    r = int(rgb[0:2], 16)
    g = int(rgb[2:4], 16)
    b = int(rgb[4:6], 16)
    c = (r + g + b) / 3.
    cc = 0
    r = r * (1 - cc) + c * cc
    g = g * (1 - cc) + c * cc
    b = b * (1 - cc) + c * cc
    h = hex(int(r))[2:] + hex(int(g))[2:] + hex(int(b))[2:]
    return "0" * (6 - len(h)) + h


def get_time_color(time):
    if not time:
        return "000000"
    time = datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")
    delta = (datetime.now() - time).total_seconds()
    time_color = hex(0xFF - min(0xFF, int(delta / 500000.)))[2:]
    i_time_color = hex(min(0xFF, int(delta / 500000.)))[2:]
    if len(time_color) == 1:
        time_color = "0" + time_color
    if len(i_time_color) == 1:
        i_time_color = "0" + i_time_color
    return time_color + "AA" + i_time_color


def glue(ways: List[OSMWay]):
    """
    Try to glue ways that share nodes.
    """
    result: List[List[int]] = []
    to_process: Set[OSMWay] = set()

    for way in ways:  # type: OSMWay
        if way.is_cycle():
            result.append(way.nodes)
        else:
            to_process.add(way)

    while to_process:
        way: OSMWay = to_process.pop()
        glued: Optional[OSMWay] = None

        for other_way in to_process:  # type: OSMWay
            glued = way.try_to_glue(other_way)
            if glued:
                break

        if glued:
            to_process.remove(other_way)
            if glued.is_cycle():
                result.append(glued.nodes)
            else:
                to_process.add(glued)
        else:
            result.append(way.nodes)

    return result


class Constructor:
    def __init__(self, check_level, mode, seed, map_, flinger, scheme):
        self.check_level = check_level
        self.mode = mode
        self.seed = seed
        self.map_ = map_
        self.flinger = flinger
        self.scheme = scheme

        self.nodes: List[Node] = []
        self.ways: List[Way] = []

    def construct_ways(self):
        for way_id in self.map_.way_map:
            way = self.map_.way_map[way_id]
            tags = way.tags
            if not self.check_level(tags):
                continue
            self.construct_way(way.nodes, tags, None, way.user, way.timestamp)

    def construct_way(self, nodes, tags, path, user, time):
        """
        Way construction.

        Params:
            :param drawing: structure for drawing elements.
            :param nodes: way node list.
            :param tags: way tag dictionary.
            :param path: way path (if there is no nodes).
            :param user: author name.
            :param user: way update time.
        """
        layer: float = 0
        level: float = 0

        if "layer" in tags:
            layer = get_float(tags["layer"])
        if "level" in tags:
            levels = list(map(lambda x: float(x), tags["level"].split(";")))
            level = sum(levels) / len(levels)

        layer = 100 * level + 0.01 * layer

        if nodes:
            c = line_center(
                map(lambda x: self.map_.node_map[x], nodes), self.flinger)

        if self.mode == "user-coloring":
            user_color = get_user_color(user, self.seed)
            self.ways.append(
                Way("way", nodes, path,
                    f"fill:none;stroke:#{user_color};stroke-width:1;"))
            return

        if self.mode == "time":
            if not time:
                return
            time_color = get_time_color(time)
            self.ways.append(
                Way("way", nodes, path,
                    f"fill:none;stroke:#{time_color};stroke-width:1;"))
            return

        # Indoor features

        if "indoor" in tags:
            v = tags["indoor"]
            style = f"stroke:{indoor_border_color};stroke-width:1;"
            if v == "area":
                style += f"fill:#{indoor_color};"
                layer += 10
            elif v == "corridor":
                style += f"fill:#{indoor_color};"
                layer += 11
            elif v in ["yes", "room", "elevator"]:
                style += f"fill:#{indoor_color};"
                layer += 12
            elif v == "column":
                style += f"fill:#{indoor_border_color};"
                layer += 13
            self.ways.append(Way("way", nodes, path, style, layer, 50))

        # Natural

        if "natural" in tags:
            v = tags["natural"]
            style = "stroke:none;"
            if v == "wood":
                style += f"fill:#{wood_color};"
                layer += 21
            elif v == "grassland":
                style = f"fill:#{grass_color};stroke:#{grass_border_color};"
                layer += 20
            elif v == "scrub":
                style += f"fill:#{wood_color};"
                layer += 21
            elif v == "sand":
                style += f"fill:#{sand_color};"
                layer += 20
            elif v == "beach":
                style += f"fill:#{beach_color};"
                layer += 20
            elif v == "desert":
                style += f"fill:#{desert_color};"
                layer += 20
            elif v == "forest":
                style += f"fill:#{wood_color};"
                layer += 21
            elif v == "tree_row":
                style += f"fill:none;stroke:#{wood_color};stroke-width:5;"
                layer += 21
            elif v == "water":
                style = f"fill:#{water_color};stroke:#{water_border_color};stroke-width:1.0;"
                layer += 21
            self.ways.append(Way("way", nodes, path, style, layer, 50))

        # Landuse

        if "landuse" in tags:
            style = "fill:none;stroke:none;"
            if tags["landuse"] == "grass":
                style = f"fill:#{grass_color};stroke:#{grass_border_color};"
                layer += 20
            elif tags["landuse"] == "conservation":
                style = f"fill:#{grass_color};stroke:none;"
                layer += 20
            elif tags["landuse"] == "forest":
                style = f"fill:#{wood_color};stroke:none;"
                layer += 20
            elif tags["landuse"] == "garages":
                style = f"fill:#{parking_color};stroke:none;"
                layer += 21
                shapes, fill, processed = \
                    process.get_icon(tags, self.scheme, "444444")
                if nodes:
                    self.nodes.append(Node(
                        shapes, tags, c[0], c[1], fill, path, processed))
            elif tags["landuse"] == "construction":
                layer += 20
                style = f"fill:#{construction_color};stroke:none;"
            elif tags["landuse"] in ["residential", "commercial"]:
                return
            self.ways.append(Way("way", nodes, path, style, layer, 50))

        # Building

        if "building" in tags:
            layer += 40
            levels = 1
            if "building:levels" in tags:
                levels = float(tags["building:levels"])
            style = f"fill:#{building_color};stroke:#" + \
                    building_border_color + ";opacity:1.0;"
            shapes, fill, processed = \
                process.get_icon(tags, self.scheme, "444444")
            if "height" in tags:
                layer += float(tags["height"])
            if nodes:
                self.nodes.append(
                    Node(shapes, tags, c[0], c[1], fill, path, processed, 1))
            self.ways.append(Way("building", nodes, path, style, layer, 50, levels))

        # Amenity

        if "amenity" in tags:
            style = "fill:none;stroke:none;"
            layer += 21
            if tags["amenity"] == "parking":
                style = f"fill:#{parking_color};stroke:none;opacity:0.5;"
                shapes, fill, processed = \
                    process.get_icon(tags, self.scheme, "444444")
                if nodes:
                    self.nodes.append(Node(
                        shapes, tags, c[0], c[1], fill, path, processed, 1))
            self.ways.append(Way("way", nodes, path, style, layer, 50))

        # Waterway

        if "waterway" in tags:
            style = "fill:none;stroke:none;"
            layer += 21
            if tags["waterway"] == "riverbank":
                style = f"fill:#{water_color};stroke:#" + \
                        water_border_color + ";stroke-width:1.0;"
            elif tags["waterway"] == "river":
                style = "fill:none;stroke:#" + water_color + ";stroke-width:10.0;"
            self.ways.append(Way("way", nodes, path, style, layer, 50))

        # Railway

        if "railway" in tags:
            style = "fill:none;stroke:none;"
            layer += 41
            v = tags["railway"]
            style = "fill:none;stroke-dasharray:none;stroke-linejoin:round;" + \
                    "stroke-linecap:round;stroke-width:"
            if v == "subway": style += "10;stroke:#DDDDDD;"
            if v in ["narrow_gauge", "tram"]:
                style += "2;stroke:#000000;"
            if v == "platform":
                style = f"fill:#{platform_color};stroke:#" + \
                        platform_border_color + "stroke-width:1;"
            else:
                return
            self.ways.append(Way("way", nodes, path, style, layer, 50))

        # Highway

        if "highway" in tags:
            layer += 42
            v = tags["highway"]
            style = \
                f"fill:none;stroke:#{road_border_color};" \
                f"stroke-dasharray:none;stroke-linejoin:round;" \
                f"stroke-linecap:round;stroke-width:"

            # Highway outline

            if v == "motorway":
                style += "33"
            elif v == "trunk":
                style += "31"
            elif v == "primary":
                style += f"29;stroke:#{primary_border_color}"
            elif v == "secondary":
                style += "27"
            elif v == "tertiary":
                style += "25"
            elif v == "unclassified":
                style += "17"
            elif v == "residential":
                style += "17"
            elif v == "service":
                if "service" in tags and tags["service"] == "parking_aisle":
                    style += "7"
                else:
                    style += "11"
            elif v == "track":
                style += "3"
            elif v in ["footway", "pedestrian", "cycleway"]:
                if not ("area" in tags and tags["area"] == "yes"):
                    style += f"3;stroke:#{foot_border_color}"
            elif v in ["steps"]:
                style += f"6;stroke:#{foot_border_color};stroke-linecap:butt;"
            else:
                style = None
            if style:
                style += ";"
                self.ways.append(Way("way", nodes, path, style, layer + 41, 50))

            # Highway main shape

            style = "fill:none;stroke:#FFFFFF;stroke-linecap:round;" + \
                    "stroke-linejoin:round;stroke-width:"

            priority = 50

            if v == "motorway":
                style += "31"
            elif v == "trunk":
                style += "29"
            elif v == "primary":
                style += "27;stroke:#" + primary_color
            elif v == "secondary":
                style += "25"
            elif v == "tertiary":
                style += "23"
            elif v == "unclassified":
                style += "15"
            elif v == "residential":
                style += "15"
            elif v == "service":
                if "service" in tags and tags["service"] == "parking_aisle":
                    style += "5"
                else:
                    style += "9"
            elif v == "cycleway":
                style += f"1;stroke-dasharray:8,2;istroke-linecap:butt;stroke:#{cycle_color}"
            elif v in ["footway", "pedestrian"]:
                priority = 55
                if "area" in tags and tags["area"] == "yes":
                    style += "1;stroke:none;fill:#DDDDDD"
                    layer -= 55  # FIXME!
                else:
                    style += "1.5;stroke-dasharray:7,3;stroke-linecap:round;" + \
                             "stroke:#"
                    if "guide_strips" in tags and tags["guide_strips"] == "yes":
                        style += guide_strips_color
                    else:
                        style += foot_color
            elif v == "steps":
                style += "5;stroke-dasharray:1.5,2;stroke-linecap:butt;" + \
                         "stroke:#"
                if "conveying" in tags:
                    style += "888888"
                else:
                    style += foot_color
            elif v == "path":
                style += "1;stroke-dasharray:5,5;stroke-linecap:butt;" + \
                         "stroke:#" + foot_color
            style += ";"
            self.ways.append(Way("way", nodes, path, style, layer + 42, 50))
            if "oneway" in tags and tags["oneway"] == "yes" or \
                    "conveying" in tags and tags["conveying"] == "forward":
                for k in range(7):
                    self.ways.append(Way(
                        "way", nodes, path,
                        f"fill:none;stroke:#EEEEEE;stroke-linecap:butt;stroke-width:{7 - k};stroke-dasharray:{k},{40 - k};",
                        layer + 43, 50))
            if "access" in tags and tags["access"] == "private":
                self.ways.append(Way(
                    "way", nodes, path,
                    f"fill:none;stroke:#{private_access_color};"
                    f"stroke-linecap:butt;stroke-width:10;stroke-dasharray:1,5;"
                    f"opacity:0.4;", layer + 0.1, 50))

        # Leisure

        if "leisure" in tags:
            style = "fill:none;stroke:none;"
            layer += 21
            if tags["leisure"] == "playground":
                style = f"fill:#{playground_color};opacity:0.2;"
                # FIXME!!!!!!!!!!!!!!!!!!!!!
                # if nodes:
                #     self.draw_point_shape("toy_horse", c[0], c[1], "444444")
            elif tags["leisure"] == "garden":
                style = f"fill:#{grass_color};"
            elif tags["leisure"] == "pitch":
                style = f"fill:#{playground_color};opacity:0.2;"
            elif tags["leisure"] == "park":
                return
            else:
                style = "fill:#FF0000;opacity:0.2;"
            self.ways.append(Way("way", nodes, path, style, layer, 50))

        # Barrier

        if "barrier" in tags:
            style = "fill:none;stroke:none;"
            layer += 40
            if tags["barrier"] == "hedge":
                style += "fill:none;stroke:#" + wood_color + ";stroke-width:4;"
            elif tags["barrier"] == "fense":
                style += "fill:none;stroke:#000000;stroke-width:1;opacity:0.4;"
            elif tags["barrier"] == "kerb":
                style += "fill:none;stroke:#000000;stroke-width:1;opacity:0.2;"
            else:
                style += "fill:none;stroke:#000000;stroke-width:1;opacity:0.3;"
            self.ways.append(Way("way", nodes, path, style, layer, 50))

        # Border

        if "border" in tags:
            style = "fill:none;stroke:none;"
            style += "fill:none;stroke:#FF0000;stroke-width:0.5;" + \
                     "stroke-dahsarray:10,20;"
            self.ways.append(Way("way", nodes, path, style, layer, 50))
        if "area:highway" in tags:
            style = "fill:none;stroke:none;"
            if tags["area:highway"] == "yes":
                style += "fill:#FFFFFF;stroke:#DDDDDD;stroke-width:1;"
            self.ways.append(Way("way", nodes, path, style, layer, 50))
        # drawing["ways"].append({"kind": "way", "nodes": nodes, "layer": layer,
        #    "priority": 50, "style": style, "path": path})
        """
        if False:
            if "highway" in tags and tags["highway"] != "steps" and not (
                    "surface" in tags):
                drawing["ways"].append({"kind": "way", "nodes": nodes,
                                        "layer": layer + 0.1, "priority": 50,
                                        "path": path,
                                        "style": "fill:none;" + \
                                                 "stroke:#FF0000;stroke-linecap:butt;" + \
                                                 "stroke-width:5;opacity:0.4;"})
                # draw_text("no surface", cx, cy, "FF0000", out_opacity="1.0",
                #    out_fill_2="FF0000", out_opacity_2=1.0)
        """

    def construct_relations(self):
        for relation_id in self.map_.relation_map:
            relation = self.map_.relation_map[relation_id]
            tags = relation.tags
            if not self.check_level(tags):
                continue
            if "type" in tags and tags["type"] == "multipolygon":
                inners, outers = [], []
                for member in relation.members:
                    if member["type"] == "way":
                        if member["role"] == "inner":
                            if member["ref"] in self.map_.way_map:
                                inners.append(self.map_.way_map[member["ref"]])
                        elif member["role"] == "outer":
                            if member["ref"] in self.map_.way_map:
                                outers.append(self.map_.way_map[member["ref"]])
                p = ""
                inners_path = glue(inners)
                outers_path = glue(outers)
                for way in outers_path:
                    path = get_path(way, [0, 0], self.map_, self.flinger)
                    p += path + " "
                for way in inners_path:
                    way.reverse()
                    path = get_path(way, [0, 0], self.map_, self.flinger)
                    p += path + " "
                self.construct_way(None, tags, p, "", None)

    def construct_nodes(self):
        """
        Draw nodes.
        """
        print("Draw nodes...")

        start_time = datetime.now()

        node_number = 0
        # processed_tags = 0
        # skipped_tags = 0

        s = sorted(self.map_.node_map.keys(), key=lambda x: -self.map_.node_map[x].lat)

        for node_id in s:
            node_number += 1
            ui.write_line(node_number, len(self.map_.node_map))
            node = self.map_.node_map[node_id]
            flinged = self.flinger.fling(Geo(node.lat, node.lon))
            x = flinged[0]
            y = flinged[1]
            tags = node.tags

            if not self.check_level(tags):
                continue

            shapes, fill, processed = process.get_icon(tags, self.scheme)

            if self.mode == "user-coloring":
                fill = get_user_color(node.user, self.seed)
            if self.mode == "time":
                fill = get_time_color(node.timestamp)

            # for k in tags:
            #     if k in processed or self.no_draw(k):
            #         processed_tags += 1
            #     else:
            #         skipped_tags += 1

            # for k in []:  # tags:
            #     if to_write(k):
            #         draw_text(k + ": " + tags[k], x, y + 18 + text_y, "444444")
            #         text_y += 10

            # if show_missed_tags:
            #     for k in tags:
            #         v = tags[k]
            #         if not no_draw(k) and not k in processed:
            #             if ("node " + k + ": " + v) in missed_tags:
            #                 missed_tags["node " + k + ": " + v] += 1
            #             else:
            #                 missed_tags["node " + k + ": " + v] = 1

            if shapes == [] and tags != {}:
                shapes = [["no"]]

            self.nodes.append(Node(
                shapes, tags, x, y, fill, None, processed))

        ui.write_line(-1, len(self.map_.node_map))
        print("Nodes painted in " + str(datetime.now() - start_time) + ".")
        # print("Tags processed: " + str(processed_tags) + ", tags skipped: " +
        #       str(skipped_tags) + " (" +
        #       str(processed_tags / float(
        #           processed_tags + skipped_tags) * 100) + " %).")


# Nodes drawing

class Painter:

    def __init__(
            self, show_missed_tags, overlap, draw_nodes, mode, draw_captions,
            map_, flinger, output_file, icons, scheme):

        self.show_missed_tags = show_missed_tags
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
            flinged = self.flinger.fling(node)
            self.output_file.circle(flinged[0], flinged[1], 0.2, color="FFFFFF")

    def no_draw(self, key):
        if key in self.scheme["tags_to_write"] or key in self.scheme["tags_to_skip"]:
            return True
        for prefix in self.scheme["prefix_to_write"].union(self.scheme["prefix_to_skip"]):
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

        if self.show_missed_tags:
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
                    flinged_1 = self.flinger.fling(Geo(node_1.lat, node_1.lon))
                    flinged_2 = self.flinger.fling(Geo(node_2.lat, node_2.lon))
                    self.output_file.write(
                        f'<path d="M '
                        f'{flinged_1[0] + shift_1[0]},{flinged_1[1] + shift_1[1]} L '
                        f"{flinged_2[0] + shift_1[0]},{flinged_2[1] + shift_1[1]} "
                        f"{flinged_2[0] + shift_2[0]},{flinged_2[1] + shift_2[1]} "
                        f'{flinged_1[0] + shift_2[0]},{flinged_1[1] + shift_2[1]} Z" '
                        f'style="fill:#{color};stroke:#{color};stroke-width:1;" />\n')
            elif way.path:
                # TODO: implement
                pass

    def draw(self, nodes, ways, points):

        ways = sorted(ways, key=lambda x: x.layer)
        for way in ways:
            if way.kind == "way":
                if way.nodes:
                    path = get_path(way.nodes, [0, 0], self.map_, self.flinger)
                    self.output_file.write(f'<path d="{path}" ' +
                                      'style="' + way.style + '" />\n')
                else:
                    self.output_file.write('<path d="' + way.path + '" ' +
                                      'style="' + way.style + '" />\n')

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
                        flinged_1 = self.flinger.fling(Geo(node_1.lat, node_1.lon))
                        flinged_2 = self.flinger.fling(Geo(node_2.lat, node_2.lon))
                        self.output_file.write(
                            f'<path d="M '
                            f'{flinged_1[0]},{flinged_1[1]} L '
                            f"{flinged_2[0]},{flinged_2[1]} "
                            f"{flinged_2[0] + shift[0]},{flinged_2[1] + shift[1]} "
                            f'{flinged_1[0] + shift[0]},{flinged_1[1] + shift[1]} Z" '
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
                    self.output_file.write('<path d="' + path + '" ' +
                                      'style="' + way.style + ';opacity:1;" />\n')
                else:
                    self.output_file.write(
                        '<path d="' + way.path + '" ' + 'style="' +
                        way.style + '" />\n')

        # Trees

        for node in nodes:
            if not("natural" in node.tags and
                   node.tags["natural"] == "tree" and
                   "diameter_crown" in node.tags):
                continue
            for i in range(8):
                self.output_file.circle(
                    float(node.x) + (random.random() - 0.5) * 10,
                    float(node.y) + (random.random() - 0.5) * 10,
                    float(node.tags["diameter_crown"]) * 1.5,
                    color='688C44', fill='688C44', opacity=0.2)

        # All other nodes

        nodes = sorted(nodes, key=lambda x: x.layer)
        for node in nodes:
            if "natural" in node.tags and \
                   node.tags["natural"] == "tree" and \
                   "diameter_crown" in node.tags:
                continue
            self.draw_shapes(node.shapes, points, node.x, node.y,
                        node.color, node.tags, node.processed)

        for node in nodes:
            self.draw_texts(node.shapes, points, node.x, node.y,
                        node.color, node.tags, node.processed)

    def draw_point_shape(self, name, x, y, fill, tags=None):
        if not isinstance(name, list):
            name = [name]
        for one_name in name:
            shape, xx, yy = self.icons.get_path(one_name)
            self.draw_point_outline(shape, x, y, fill, mode=self.mode, size=16, xx=xx, yy=yy)
        for one_name in name:
            shape, xx, yy = self.icons.get_path(one_name)
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
        outline_fill = outline_color
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
        levels = map(lambda x: float(x),
                     tags["level"].replace(",", ".").split(";"))
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
    options = ui.parse_options(sys.argv)

    if not options:
        sys.exit(1)

    background_color = "EEEEEE"  # "DDDDDD"
    if options.mode in ["user-coloring", "time"]:
        background_color = "111111"
        outline_color = "111111"

    input_file_name = options.input_file_name

    if not os.path.isfile(input_file_name):
        print("Fatal: no such file: " + input_file_name + ".")
        sys.exit(1)

    full = False  # Full keys getting

    if options.mode in ["user-coloring", "time"]:
        full = True

    osm_reader = OSMReader(input_file_name)

    map_ = osm_reader.parse_osm_file(
        parse_ways=options.draw_ways, parse_relations=options.draw_ways,
        full=full)

    output_file = svg.SVG(open(options.output_file_name, "w+"))

    w, h = list(map(lambda x: float(x), options.size.split(",")))

    output_file.begin(w, h)
    output_file.write(
        "<title>Rӧntgen</title><style>path:hover {stroke: #FF0000;}</style>\n")
    output_file.rect(0, 0, w, h, color=background_color)

    if "boundary_box" in options:
        bb = options.boundary_box
        min1 = Geo(bb[1], bb[0])
        max1 = Geo(bb[3], bb[2])

    authors = {}
    missed_tags = {}
    points = []

    scheme = yaml.load(open(tags_file_name), Loader=yaml.FullLoader)
    scheme["cache"] = {}
    w3c_colors = yaml.load(open(colors_file_name), Loader=yaml.FullLoader)
    for color_name in w3c_colors:
        scheme["colors"][color_name] = w3c_colors[color_name]

    flinger = GeoFlinger(min1, max1, [0, 0], [w, h])

    icons = extract_icon.IconExtractor(icons_file_name)

    check_level = lambda x: True

    if options.level:
        if options.level == "overground":
            check_level = check_level_overground
        elif options.level == "underground":
            check_level = lambda x: not check_level_overground(x)
        else:
            check_level = lambda x: check_level_number(x, float(options.level))

    constructor = Constructor(
        check_level, options.mode, options.seed, map_, flinger, scheme)
    if options.draw_ways:
        constructor.construct_ways()
        constructor.construct_relations()
    constructor.construct_nodes()

    painter = Painter(
        show_missed_tags=options.show_missed_tags, overlap=options.overlap,
        draw_nodes=options.draw_nodes, mode=options.mode,
        draw_captions=options.draw_captions,
        map_=map_, flinger=flinger, output_file=output_file, icons=icons,
        scheme=scheme)
    painter.draw(constructor.nodes, constructor.ways, points)

    if flinger.space[0] == 0:
        output_file.rect(0, 0, w, flinger.space[1], color="FFFFFF")
        output_file.rect(0, h - flinger.space[1], w, flinger.space[1], color="FFFFFF")
    if flinger.space[1] == 0:
        output_file.rect(0, 0, flinger.space[0], h, color="FFFFFF")
        output_file.rect(w - flinger.space[0], 0, flinger.space[0], h, color="FFFFFF")

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
                b = int(matrix[i][j] / 1)
                a = "%2x" % min(255, b)
                color = a + a + a
                color = color.replace(" ", "0")
                t1 = flinger.fling(Geo(min1.lat + i * lat_step,
                                       min1.lon + j * lon_step))
                t2 = flinger.fling(Geo(min1.lat + (i + 1) * lat_step,
                                       min1.lon + (j + 1) * lon_step))
                # output_file.write("<path d = "M " + str(t1[0]) + "," +
                # str(t1[1]) + " L " + str(t1[0]) + "," + str(t2[1]) + " " +
                # str(t2[0]) + "," + str(t2[1]) + " " + str(t2[0]) + "," +
                # str(t1[1])  + "" style = "fill:#" + color + ";opacity:0.5;" />\n")
                output_file.text(((t1 + t2) * 0.5)[0], ((t1 + t2) * 0.5)[1] + 40,
                                 str(int(matrix[i][j])), size=80,
                                 color="440000", opacity=0.1,
                                 align="center")

    output_file.end()

    top_missed_tags = sorted(missed_tags.keys(), key=lambda x: -missed_tags[x])
    missed_tags_file = open(missed_tags_file_name, "w+")
    for tag in top_missed_tags:
        missed_tags_file.write("- {tag: "" + tag + "", count: " + \
                               str(missed_tags[tag]) + "}\n")
    missed_tags_file.close()

    top_authors = sorted(authors.keys(), key=lambda x: -authors[x])
    for author in top_authors:
        print(author + ": " + str(authors[author]))
