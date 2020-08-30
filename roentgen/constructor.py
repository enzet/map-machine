import numpy as np

from hashlib import sha256

from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from roentgen import process, ui
from roentgen.flinger import Geo, GeoFlinger
from roentgen.osm_reader import OSMMember, OSMRelation, OSMWay
from roentgen.scheme import Scheme


class Node:
    """
    Node in Röntgen terms.
    """
    def __init__(
            self, shapes, tags: Dict[str, str], x: float, y: float, color: str,
            path: Optional[str], processed, priority: int = 0):
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
    """
    Way in Röntgen terms.
    """
    def __init__(
            self, kind: str, nodes, path, style, layer: float = 0.0,
            priority: float = 0, levels=None):
        self.kind = kind
        self.nodes = nodes
        self.path = path
        self.style = style
        self.layer = layer
        self.priority = priority
        self.levels = levels


def get_float(string):
    """
    Try to parse float from a string.
    """
    try:
        return float(string)
    except ValueError:
        return 0


def line_center(nodes, flinger: GeoFlinger):
    """
    Get geometric center of nodes set.
    """
    ma = [0, 0]
    mi = [10000, 10000]
    for node in nodes:
        flung = flinger.fling(Geo(node.lat, node.lon))
        if flung[0] > ma[0]:
            ma[0] = flung[0]
        if flung[1] > ma[1]:
            ma[1] = flung[1]
        if flung[0] < mi[0]:
            mi[0] = flung[0]
        if flung[1] < mi[1]:
            mi[1] = flung[1]
    return [(ma[0] + mi[0]) / 2.0, (ma[1] + mi[1]) / 2.0]


def get_user_color(text: str, seed: str):
    """
    Generate random color based on text.
    """
    if text == "":
        return "000000"
    rgb = sha256((seed + text).encode("utf-8")).hexdigest()[-6:]
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
    """
    Generate color based on time.
    """
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


def get_path(nodes, shift, map_, flinger: GeoFlinger):
    """
    Construct SVG path from nodes.
    """
    path = ""
    prev_node = None
    for node_id in nodes:
        node = map_.node_map[node_id]
        flung = np.add(flinger.fling(Geo(node.lat, node.lon)), shift)
        path += ("L" if prev_node else "M") + f" {flung[0]},{flung[1]} "
        prev_node = map_.node_map[node_id]
    if nodes[0] == nodes[-1]:
        path += "Z"
    else:
        path = path[:-1]
    return path


class Constructor:
    """
    Röntgen node and way constructor.
    """
    def __init__(self, check_level, mode, seed, map_, flinger, scheme: Scheme):
        self.check_level = check_level
        self.mode = mode
        self.seed = seed
        self.map_ = map_
        self.flinger = flinger
        self.scheme: Scheme = scheme

        self.nodes: List[Node] = []
        self.ways: List[Way] = []

    def color(self, name: str):
        """
        Get color from the scheme.
        """
        return self.scheme.get_color(name)

    def construct_ways(self):
        """
        Construct Röntgen ways.
        """
        for way_id in self.map_.way_map:  # type: int
            way: OSMWay = self.map_.way_map[way_id]
            if not self.check_level(way.tags):
                continue
            self.construct_way(way, way.tags, None)

    def construct_way(
            self, way: Optional[OSMWay], tags: Dict[str, Any],
            path: Optional[str]) -> None:
        """
        Way construction.

        :param way: OSM way.
        :param tags: way tag dictionary.
        :param path: way path (if there is no nodes).
        """
        layer: float = 0
        level: float = 0

        if "layer" in tags:
            layer = get_float(tags["layer"])
        if "level" in tags:
            try:
                levels = list(map(lambda x: float(x), tags["level"].split(";")))
                level = sum(levels) / len(levels)
            except ValueError:
                pass

        layer = 100 * level + 0.01 * layer

        nodes = None

        if way:
            c = line_center(
                map(lambda x: self.map_.node_map[x], way.nodes), self.flinger)
            nodes = way.nodes

        if self.mode == "user-coloring":
            if not way:
                return
            user_color = get_user_color(way.user, self.seed)
            self.ways.append(
                Way("way", nodes, path,
                    f"fill:none;stroke:#{user_color};"
                    f"stroke-width:1;"))
            return

        if self.mode == "time":
            if not way:
                return
            time_color = get_time_color(way.timestamp)
            self.ways.append(
                Way("way", nodes, path,
                    f"fill:none;stroke:#{time_color};"
                    f"stroke-width:1;"))
            return

        # Indoor features

        if "indoor" in tags:
            v = tags["indoor"]
            style = \
                f"stroke:#{self.color('indoor_border_color')};" \
                f"stroke-width:1;"
            if v == "area":
                style += f"fill:#{self.color('indoor_color')};"
                layer += 10
            elif v == "corridor":
                style += f"fill:#{self.color('indoor_color')};"
                layer += 11
            elif v in ["yes", "room", "elevator"]:
                style += f"fill:#{self.color('indoor_color')};"
                layer += 12
            elif v == "column":
                style += f"fill:#{self.color('indoor_border_color')};"
                layer += 13
            self.ways.append(Way("way", nodes, path, style, layer, 50))

        # Natural

        if "natural" in tags:
            v = tags["natural"]
            style = "stroke:none;"
            if v == "wood":
                style += f"fill:#{self.color('wood_color')};"
                layer += 21
            elif v == "grassland":
                style = \
                    f"fill:#{self.color('grass_color')};" \
                    f"stroke:#{self.color('grass_border_color')};"
                layer += 20
            elif v == "scrub":
                style += f"fill:#{self.color('wood_color')};"
                layer += 21
            elif v == "sand":
                style += f"fill:#{self.color('sand_color')};"
                layer += 20
            elif v == "beach":
                style += f"fill:#{self.color('beach_color')};"
                layer += 20
            elif v == "desert":
                style += f"fill:#{self.color('desert_color')};"
                layer += 20
            elif v == "forest":
                style += f"fill:#{self.color('wood_color')};"
                layer += 21
            elif v == "tree_row":
                style += \
                    f"fill:none;stroke:#{self.color('wood_color')};" \
                    f"stroke-width:5;"
                layer += 21
            elif v == "water":
                style = \
                    f"fill:#{self.color('water_color')};" \
                    f"stroke:#{self.color('water_border_color')};" \
                    f"stroke-width:1.0;"
                layer += 21
            self.ways.append(Way("way", nodes, path, style, layer, 50))

        # Landuse

        if "landuse" in tags:
            style = "fill:none;stroke:none;"
            if tags["landuse"] == "grass":
                style = \
                    f"fill:#{self.color('grass_color')};" \
                    f"stroke:#{self.color('grass_border_color')};"
                layer += 20
            elif tags["landuse"] == "conservation":
                style = f"fill:#{self.color('grass_color')};stroke:none;"
                layer += 20
            elif tags["landuse"] == "forest":
                style = f"fill:#{self.color('wood_color')};stroke:none;"
                layer += 20
            elif tags["landuse"] == "garages":
                style = f"fill:#{self.color('parking_color')};stroke:none;"
                layer += 21
                shapes, fill, processed = self.scheme.get_icon(tags)
                if way:
                    self.nodes.append(Node(
                        shapes, tags, c[0], c[1], fill, path, processed))
            elif tags["landuse"] == "construction":
                layer += 20
                style = f"fill:#{self.color('construction_color')};stroke:none;"
            elif tags["landuse"] in ["residential", "commercial"]:
                return
            self.ways.append(Way("way", nodes, path, style, layer, 50))

        # Building

        if "building" in tags:
            layer += 40
            levels = 1
            if "building:levels" in tags:
                levels = float(tags["building:levels"])
            style = \
                f"fill:#{self.color('building_color')};" \
                f"stroke:#{self.color('building_border_color')};" \
                f"opacity:1.0;"
            shapes, fill, processed = self.scheme.get_icon(tags)
            if "height" in tags:
                try:
                    layer += float(tags["height"])
                except ValueError:
                    pass
            if way:
                self.nodes.append(
                    Node(shapes, tags, c[0], c[1], fill, path, processed, 1))
            self.ways.append(Way(
                "building", nodes, path, style, layer, 50, levels))

        # Amenity

        if "amenity" in tags:
            style = "fill:none;stroke:none;"
            layer += 21
            if tags["amenity"] == "parking":
                style = \
                    f"fill:#{self.color('parking_color')};" \
                    f"stroke:none;opacity:0.5;"
                shapes, fill, processed = self.scheme.get_icon(tags)
                if way:
                    self.nodes.append(Node(
                        shapes, tags, c[0], c[1], fill, path, processed, 1))
            self.ways.append(Way("way", nodes, path, style, layer, 50))

        # Waterway

        if "waterway" in tags:
            style = "fill:none;stroke:none;"
            layer += 21
            if tags["waterway"] == "riverbank":
                style = \
                    f"fill:#{self.color('water_color')};" \
                    f"stroke:#{self.color('water_border_color')};" \
                    f"stroke-width:1.0;"
            elif tags["waterway"] == "river":
                style = \
                    f"fill:none;stroke:#{self.color('water_color')};" \
                    f"stroke-width:10.0;"
            self.ways.append(Way("way", nodes, path, style, layer, 50))

        # Railway

        if "railway" in tags:
            layer += 41
            v = tags["railway"]
            style = \
                "fill:none;stroke-dasharray:none;stroke-linejoin:round;" \
                "stroke-linecap:round;stroke-width:"
            if v == "subway":
                style += "10;stroke:#DDDDDD;"
            if v in ["narrow_gauge", "tram"]:
                style += "2;stroke:#000000;"
            if v == "platform":
                style = \
                    f"fill:#{self.color('platform_color')};" \
                    f"stroke:#{self.color('platform_border_color')};" \
                    f"stroke-width:1;"
            else:
                return
            self.ways.append(Way("way", nodes, path, style, layer, 50))

        # Highway

        if "highway" in tags:
            layer += 42
            v = tags["highway"]
            style = \
                f"fill:none;stroke:#{self.color('road_border_color')};" \
                f"stroke-dasharray:none;stroke-linejoin:round;" \
                f"stroke-linecap:round;stroke-width:"

            # Highway outline

            if v == "motorway":
                style += "33"
            elif v == "trunk":
                style += "31"
            elif v == "primary":
                style += f"29;stroke:#{self.color('primary_border_color')};"
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
                    style += f"3;stroke:#{self.color('foot_border_color')};"
            elif v in ["steps"]:
                style += \
                    f"6;stroke:#{self.color('foot_border_color')};" \
                    f"stroke-linecap:butt;"
            else:
                style = None
            if style:
                style += ";"
                self.ways.append(Way(
                    "way", nodes, path, style, layer + 41, 50))

            # Highway main shape

            style = "fill:none;stroke:#FFFFFF;stroke-linecap:round;" + \
                    "stroke-linejoin:round;stroke-width:"

            if v == "motorway":
                style += "31"
            elif v == "trunk":
                style += "29"
            elif v == "primary":
                style += "27;stroke:#" + self.color('primary_color')
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
                style += \
                    f"1;stroke-dasharray:8,2;istroke-linecap:butt;" \
                    f"stroke:#{self.color('cycle_color')}"
            elif v in ["footway", "pedestrian"]:
                if "area" in tags and tags["area"] == "yes":
                    style += "1;stroke:none;fill:#DDDDDD"
                    layer -= 55  # FIXME!
                else:
                    style += \
                        "1.5;stroke-dasharray:7,3;stroke-linecap:round;stroke:#"
                    if "guide_strips" in tags and tags["guide_strips"] == "yes":
                        style += self.color('guide_strips_color')
                    else:
                        style += self.color('foot_color')
            elif v == "steps":
                style += "5;stroke-dasharray:1.5,2;stroke-linecap:butt;" + \
                         "stroke:#"
                if "conveying" in tags:
                    style += "888888"
                else:
                    style += self.color('foot_color')
            elif v == "path":
                style += "1;stroke-dasharray:5,5;stroke-linecap:butt;" + \
                         "stroke:#" + self.color('foot_color')
            style += ";"
            self.ways.append(Way("way", nodes, path, style, layer + 42, 50))
            if "oneway" in tags and tags["oneway"] == "yes" or \
                    "conveying" in tags and tags["conveying"] == "forward":
                for k in range(7):
                    self.ways.append(Way(
                        "way", nodes, path,
                        f"fill:none;stroke:#EEEEEE;stroke-linecap:butt;"
                        f"stroke-width:{7 - k};stroke-dasharray:{k},{40 - k};",
                        layer + 43, 50))
            if "access" in tags and tags["access"] == "private":
                self.ways.append(Way(
                    "way", nodes, path,
                    f"fill:none;stroke:#{self.color('private_access_color')};"
                    f"stroke-linecap:butt;stroke-width:10;stroke-dasharray:1,5;"
                    f"opacity:0.4;", layer + 0.1, 50))

        # Leisure

        if "leisure" in tags:
            layer += 21
            if tags["leisure"] == "playground":
                style = f"fill:#{self.color('playground_color')};opacity:0.2;"
                # FIXME!!!!!!!!!!!!!!!!!!!!!
                # if nodes:
                #     self.draw_point_shape("toy_horse", c[0], c[1], "444444")
            elif tags["leisure"] == "garden":
                style = f"fill:#{self.color('grass_color')};"
            elif tags["leisure"] == "pitch":
                style = f"fill:#{self.color('playground_color')};opacity:0.2;"
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
                style += \
                    f"fill:none;stroke:#{self.color('wood_color')};" \
                    f"stroke-width:4;"
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

    def construct_relations(self):
        """
        Construct Röntgen ways from OSM relations.
        """
        for relation_id in self.map_.relation_map:
            relation: OSMRelation = self.map_.relation_map[relation_id]
            tags = relation.tags
            if not self.check_level(tags):
                continue
            if "type" in tags and tags["type"] == "multipolygon":
                inners, outers = [], []
                for member in relation.members:  # type: OSMMember
                    if member.type_ == "way":
                        if member.role == "inner":
                            if member.ref in self.map_.way_map:
                                inners.append(self.map_.way_map[member.ref])
                        elif member.role == "outer":
                            if member.ref in self.map_.way_map:
                                outers.append(self.map_.way_map[member.ref])
                p = ""
                inners_path = glue(inners)
                outers_path = glue(outers)
                for nodes in outers_path:
                    path = get_path(nodes, [0, 0], self.map_, self.flinger)
                    p += path + " "
                for nodes in inners_path:
                    nodes.reverse()
                    path = get_path(nodes, [0, 0], self.map_, self.flinger)
                    p += path + " "
                self.construct_way(None, tags, p)

    def construct_nodes(self):
        """
        Draw nodes.
        """
        print("Draw nodes...")

        start_time = datetime.now()

        node_number: int = 0

        s = sorted(
            self.map_.node_map.keys(), key=lambda x: -self.map_.node_map[x].lat)

        for node_id in s:  # type: int
            node_number += 1
            ui.write_line(node_number, len(self.map_.node_map))
            node = self.map_.node_map[node_id]
            flung = self.flinger.fling(Geo(node.lat, node.lon))
            x = flung[0]
            y = flung[1]
            tags = node.tags

            if not self.check_level(tags):
                continue

            shapes, fill, processed = self.scheme.get_icon(tags)

            if self.mode in ["time", "user-coloring"]:
                if not tags:
                    continue
                shapes = ["small"]
            if self.mode == "user-coloring":
                fill = get_user_color(node.user, self.seed)
            if self.mode == "time":
                fill = get_time_color(node.timestamp)

            if shapes == [] and tags != {}:
                shapes = [["no"]]

            self.nodes.append(Node(
                shapes, tags, x, y, fill, None, processed))

        ui.write_line(-1, len(self.map_.node_map))

        print("Nodes painted in " + str(datetime.now() - start_time) + ".")
