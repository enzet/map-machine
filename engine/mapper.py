#!/usr/bin/python
# -*- coding: utf-8 -*- from __future__ import unicode_literals

"""
Simple tool for working with OpenStreetMap data.

Author: Sergey Vartanov (me@enzet.ru).
"""

import copy
import datetime
import os
import process
import re
import sys
import xml.dom.minidom
import yaml

import extract_icon
import osm_reader
import ui

from flinger import GeoFlinger, Geo

sys.path.append('../lib')

import svg
from vector import Vector

background_color = 'EEEEEE'
building_color = 'D4D4D4'  # 'D0D0C0'
building_border_color = 'C4C4C4'  # 'AAAAAA'
construction_color = 'CCCCCC'
grass_color = 'C8DC94'
sand_color = 'F0E0D0'
beach_color = 'F0E0C0'
desert_color = 'F0E0D0'
parking_color = 'DDCC99'
playground_color = '884400'
primary_border_color = '888888'  # 'AA8800'
primary_color = 'FFFFFF'  # 'FFDD66'
water_color = 'AACCFF'
water_border_color = '6688BB'
wood_color = 'B8CC84'

icons_file_name = '../icons/icons.svg'
tags_file_name = '../data/tags.yml'
colors_file_name = '../data/colors.yml'
missed_tags_file_name = '../missed_tags.yml'

tags_to_write = set(['operator', 'opening_hours', 'cuisine', 'network',  
                 'website', 'website_2', 'STIF:zone', 'opening_hours:url',
                 'phone', 'branch', 'route_ref', 'brand', 'ref', 'wikipedia', 
                 'description', 'level', 'wikidata', 'name', 'alt_name', 
                 'image', 'fax', 'old_name', 'artist_name', 'int_name',
                 'official_name', 'full_name', 'email', 'designation', 
                 'min_height', 'height', 'inscription', 'start_date', 
                 'created_by', 'naptan:verified', 'url', 'naptan:AtcoCode',
                 'naptan:Landmark', 'naptan:Indicator', 'collection_times',
                 'naptan:Street', 'naptan:PlusbusZoneRef', 'naptan:Crossing',
                 'local_ref', 'naptan:CommonName', 'survey:date', 
                 'naptan:NaptanCode', 'postal_code', 'uk_postcode_centroid',
                 'fhrs:rating_date', 'fhrs:local_authority_id', 'destination',
                 'fhrs:id', 'naptan:ShortCommonName', 'flickr', 'royal_cypher',
                 'is_in', 'booth', 'naptan:AltStreet', 'media:commons', 
                 'ref_no', 'uri', 'fhrs:inspectiondate', 'telephone', 
                 'naptan:AltCommonName', 'end_date', 'facebook', 'naptan:Notes',
                 'voltage', 'last_collection', 'twitter', 'ele', 'information',
                 'phone_1', 'cyclestreets_id', 'cladr:code',
                 # To draw
                 'naptan:Bearing', 'species', 'taxon', 'seats', 'capacity',
                 'fhrs:rating', 'fhrs:confidence_management', 'fhrs:hygiene',
                 'genus', 'platforms', 'naptan:BusStopType'])

prefix_to_write = set(['addr', 'contact', 'name', 'operator', 'wikipedia', 
                   'alt_name', 'description', 'old_name', 'inscription', 
                   'route_ref', 'is_in', 'website', 'ref',
                   # To draw
                   'species', 'taxon', 'genus'])

tags_to_skip = set(['note', 'layer', 'source', 'building:part', 'fixme', 'comment',
        'FIXME', 'source_ref', 'naptan:verified:note', 'building:levels'])

prefix_to_skip = set(['source'])

def get_d_from_file(file_name):
    path, x, y = icons.get_path(file_name)
    if path:
        return path, x, y
    else:
        # print 'No such icon: ' + file_name
        # TODO: add to missed icons
        return 'M 4,4 L 4,10 10,10 10,4 z', 0, 0


def get_min_max(node_map):
    key = node_map.keys()[0]
    maximum = Geo(node_map[key]['lon'], node_map[key]['lat'])
    minimum = Geo(node_map[key]['lon'], node_map[key]['lat'])
    for node_id in node_map:
        node = node_map[node_id]
        if node['lat'] > maximum.lat: maximum.lat = node['lat']
        if node['lat'] < minimum.lat: minimum.lat = node['lat']
        if node['lon'] > maximum.lon: maximum.lon = node['lon']
        if node['lon'] < minimum.lon: minimum.lon = node['lon']
    return minimum, maximum


def draw_path(nodes, style, shift=Vector()):
    prev_node = None
    for node_id in nodes:
        node = node_map[node_id]
        flinged1 = flinger.fling(Geo(node['lat'], node['lon'])) + shift
        if prev_node:
            flinged2 = flinger.fling(Geo(prev_node['lat'], prev_node['lon'])) + shift
            output_file.write('L ' + `flinged1.x` + ',' + `flinged1.y` + ' ')
        else:
            output_file.write('<path d="M ' + `flinged1.x` + \
                ',' + `flinged1.y` + ' ')
        prev_node = node_map[node_id]
    output_file.write('" style="' + style + '" />\n')

def draw_point_shape(name, x, y, fill):
    if not isinstance(name, list):
        name = [name]
    for one_name in name:
        shape, xx, yy = get_d_from_file(one_name)
        draw_point_outline(shape, x, y, fill, size=16, xx=xx, yy=yy)
    for one_name in name:
        shape, xx, yy = get_d_from_file(one_name)
        draw_point(shape, x, y, fill, size=16, xx=xx, yy=yy)

def draw_point_outline(shape, x, y, fill, size=16, xx=0, yy=0):
    x = int(float(x))
    y = int(float(y))
    outline_fill = 'FFFFFF'
    opacity = 0.5
    r = int(fill[0:2], 16)
    g = int(fill[2:4], 16)
    b = int(fill[4:6], 16)
    Y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    if Y > 200:
        outline_fill = '000000'
        opacity = 0.3
    output_file.write('<path d="' + shape + \
        '" style="fill:#' + outline_fill + ';opacity:' + str(opacity) + ';' + \
        'stroke:#' + outline_fill + ';stroke-width:3;stroke-linejoin:round;" ' + \
        'transform="translate(' + \
         str(x - size / 2.0 - xx * 16) + ',' + str(y - size / 2.0 - yy * 16) + ')" />\n')

def draw_point(shape, x, y, fill, size=16, xx=0, yy=0):
    x = int(float(x))
    y = int(float(y))
    output_file.write('<path d="' + shape + \
         '" style="fill:#' + fill + ';fill-opacity:1" transform="translate(' + \
         str(x - size / 2.0 - xx * 16) + ',' + str(y - size / 2.0 - yy * 16) + ')" />\n')

def draw_text(text, x, y, fill):
    if type(text) == unicode:
        text = text.encode('utf-8')
    text = text.replace('&', 'and')
    if text[:7] == 'http://' or text[:8] == 'https://':
        text = 'link'
        fill = '0000FF'
    output_file.write('<text x="' + str(x) + '" y="' + str(y) + \
            '" style="font-size:10;text-anchor:middle;font-family:Myriad Pro;fill:#FFFFFF;stroke-linejoin:round;stroke-width:5;stroke:#FFFFFF;opacity:0.5;">' + text + '</text>')
    output_file.write('<text x="' + str(x) + '" y="' + str(y) + \
            '" style="font-size:10;text-anchor:middle;font-family:Myriad Pro;fill:#' + fill + ';">' + text + '</text>')

def point(k, v, x, y, fill, text_y):
    text = k + ': ' + v
    if type(text) == unicode:
        text = text.encode('utf-8')
    draw_text(text, x, float(y) + text_y + 18, '734A08')

# Ways drawing

def construct_layers():
    """
    Construct layers. One layer may contain elements of different types.
    """
    layers = {}

    for way_id in way_map:
        way = way_map[way_id]
        if not ('layer' in way['tags']):
            way['tags']['layer'] = 0
        if not (float(way['tags']['layer']) in layers):
            layers[float(way['tags']['layer'])] = \
                {'b': [], 'h1': [], 'h2': [], 'r': [], 'n': [], 'l': [],
                 'a': [], 'le': [], 'ba': [], 'bo': [], 'w': []}
        layer = layers[float(way['tags']['layer'])]
        if 'building' in way['tags']:
            layer['b'].append(way)
        if 'natural' in way['tags']:
            layer['n'].append(way)
        if 'landuse' in way['tags']:
            layer['l'].append(way)
        if 'railway' in way['tags']:
            layer['r'].append(way)
        if 'amenity' in way['tags']:
            layer['a'].append(way)
        if 'leisure' in way['tags']:
            layer['le'].append(way)
        if 'barrier' in way['tags']:
            layer['ba'].append(way)
        if 'highway' in way['tags']:
            layer['h1'].append(way)
            layer['h2'].append(way)
        if 'boundary' in way['tags']:
            layer['bo'].append(way)
        if 'waterway' in way['tags']:
            layer['w'].append(way)
        #else:
        #    empty = True
        #    for key in way['tags'].keys():
        #        if not (key in ['layer', 'note']):
        #            empty = False
        #    if not empty:
        #        print 'Unknown kind of way:', way['tags']
    return layers


def draw_raw_ways():
    for way_id in way_map:
        way = way_map[way_id]
        draw_path(way['nodes'], 'stroke:#FFFFFF;fill:none;stroke-width:0.2;')

def line_center(node_ids):
    ma = Vector()
    mi = Vector(10000, 10000)
    for node_id in node_ids:
        node = node_map[node_id]
        flinged = flinger.fling(Geo(node['lat'], node['lon']))
        if flinged.x > ma.x: ma.x = flinged.x
        if flinged.y > ma.y: ma.y = flinged.y
        if flinged.x < mi.x: mi.x = flinged.x
        if flinged.y < mi.y: mi.y = flinged.y
    return Vector((ma.x + mi.x) / 2.0, (ma.y + mi.y) / 2.0)


def construct_ways(drawing):
    for way_id in way_map:
        way = way_map[way_id]
        tags = way['tags']
        nodes = way['nodes']
        if nodes[0] == nodes[-1]:
            style = 'fill:#0000FF;stroke:none;'
        else:
            style = 'stroke:#0000FF;fill:none;'
        layer = float(tags['layer']) if ('layer' in tags) else 0
        c = line_center(nodes)
        if 'landuse' in tags:
            if tags['landuse'] == 'grass':
                style = 'fill:#' + grass_color + ';stroke:none;'
            elif tags['landuse'] == 'conservation':
                style = 'fill:#' + grass_color + ';stroke:none;'
            elif tags['landuse'] == 'forest':
                style = 'fill:#' + wood_color + ';stroke:none;'
            elif tags['landuse'] == 'garages':
                style = 'fill:#' + parking_color + ';stroke:none;'
                shapes, fill, processed = process.get_icon(tags, scheme, '444444')
                drawing['nodes'].append({'shapes': shapes, 
                    'x': c.x, 'y': c.y, 'color': fill, 'processed': processed})
            elif way['tags']['landuse'] == 'construction':
                style = 'fill:#' + construction_color + ';stroke:none;'
            elif way['tags']['landuse'] in ['residential', 'commercial']:
                continue
        elif 'building' in tags:
            text_y = 0
            style = 'fill:#' + building_color + ';stroke:#' + \
                building_border_color + ';opacity:1.0;'
            shapes, fill, processed = process.get_icon(tags, scheme, '444444')
            drawing['nodes'].append({'shapes': shapes, 'x': c.x, 'y': c.y, 
                'color': fill, 'priority': 1, 'processed': processed, 
                'tags': tags})
        elif 'amenity' in tags:
            if tags['amenity'] == 'parking':
                style = 'fill:#' + parking_color + ';stroke:none;'
                draw_point_shape('parking', c.x, c.y, '444444')
        elif 'natural' in tags:
            v = way['tags']['natural']
            style = 'stroke:none;'
            if v == 'wood':
                style += 'fill:#' + wood_color + ';'
            elif v == 'scrub':
                style += 'fill:#' + wood_color + ';'
            elif v == 'sand':
                style += 'fill:#' + sand_color + ';'
            elif v == 'beach':
                style += 'fill:#' + beach_color + ';'
            elif v == 'desert':
                style += 'fill:#' + desert_color + ';'
            elif v == 'forest':
                style += 'fill:#' + wood_color + ';'
            elif v == 'water':
                style = 'fill:#' + water_color + ';stroke:#' + \
                    water_border_color + ';stroke-width:1.0;'
        elif 'waterway' in tags:
            if tags['waterway'] == 'riverbank':
                style = 'fill:#' + water_color + ';stroke:#' + \
                    water_border_color + ';stroke-width:1.0;'
            elif tags['waterway'] == 'river':
                style = 'fill:none;stroke:#' + water_color + ';stroke-width:10.0;'
        elif 'railway' in tags:
            v = tags['railway']
            style = 'fill:none;stroke-dasharray:none;stroke-linejoin:round;' + \
                'stroke-linecap:round;stroke-width:'
            if v == 'subway': style += '10;stroke:#DDDDDD;'
            if v in ['narrow_gauge', 'tram']: 
                style += '2;stroke:#000000;'
            else:
                continue
        elif 'highway' in tags:
            v = tags['highway']
            if 'tunnel' in tags and tags['tunnel'] == 'yes':
                style = 'fill:none;stroke:#FFFFFF;stroke-dasharray:none;' + \
                    'stroke-linejoin:round;stroke-linecap:round;stroke-width:10;'
                drawing['ways'].append({'kind': 'way', 'nodes': nodes, 
                    'layer': layer - 100, 'priority': 50, 'style': style})

            style = 'fill:none;stroke:#AAAAAA;stroke-dasharray:none;' + \
                'stroke-linejoin:round;stroke-linecap:round;stroke-width:'
            if v == 'motorway': style += '30'
            elif v == 'trunk': style += '25'
            elif v == 'primary': style += '20;stroke:#' + primary_border_color
            elif v == 'secondary': style += '13'
            elif v == 'tertiary': style += '11'
            elif v == 'unclassified': style += '9'
            elif v == 'residential': style += '8'
            elif v == 'service': style += '7'
            elif v == 'track': style += '3'
            else: style = None
            if style:
                style += ';'
                drawing['ways'].append({'kind': 'way', 'nodes': nodes, 
                    'layer': layer - 0.01, 'priority': 50, 'style': style})

            style = 'fill:none;stroke:#FFFFFF;stroke-linecap:round;' + \
                'stroke-linejoin:round;stroke-width:'
            if v == 'motorway': style += '28'
            elif v == 'trunk': style += '23'
            elif v == 'primary': style += '19;stroke:#' + primary_color
            elif v == 'secondary': style += '11'
            elif v == 'tertiary': style += '9'
            elif v == 'unclassified': style += '7'
            elif v == 'residential': style += '6'
            elif v == 'service': style += '5'
            elif v in ['footway', 'pedestrian']: 
                style += '1;stroke-dasharray:3,3;stroke-linecap:butt;stroke:#888888'
            elif v == 'steps': 
                style += '5;stroke-dasharray:1,2;stroke-linecap:butt;stroke:#888888'
            elif v == 'path': 
                style += '1;stroke-dasharray:5,5;stroke-linecap:butt;stroke:#888888'
            style += ';'
        elif 'leisure' in tags:
            c = line_center(way['nodes'])
            if tags['leisure'] == 'playground':
                style = 'fill:#' + playground_color + ';opacity:0.2;'
                draw_point_shape('toy_horse', c.x, c.y, '444444')
            elif tags['leisure'] == 'garden':
                style = 'fill:#' + grass_color + ';'
            elif tags['leisure'] == 'pitch':
                style = 'fill:#' + playground_color + ';opacity:0.2;'
            elif tags['leisure'] == 'park':
                continue
            else:
                style = 'fill:#FF0000;opacity:0.2;'
        elif 'barrier' in tags:
            if tags['barrier'] == 'hedge':
                style += 'fill:none;stroke:#' + wood_color + ';stroke-width:4;'
            else:
                style += 'fill:none;stroke:#000000;stroke-width:1;opacity:0.4;'
        elif 'border' in tags:
            style += 'fill:none;stroke:#FF0000;stroke-width:0.5;' + \
                'stroke-dahsarray:10,20;'
        else:
            continue
 
        drawing['ways'].append({'kind': 'way', 'nodes': nodes, 'layer': layer,
            'priority': 50, 'style': style})


# Nodes drawing

def draw_raw_nodes():
    for node_id in node_map:
        node = node_map[node_id]
        flinged = flinger.fling(node)
        output_file.circle(flinged.x, flinged.y, 0.2, color='FFFFFF')

def no_draw(key):
    if key in tags_to_write or key in tags_to_skip:
        return True
    for prefix in prefix_to_write.union(prefix_to_skip):
        if key[:len(prefix) + 1] == prefix + ':':
            return True
    return False

def to_write(key):
    if key in tags_to_write:
        return True
    for prefix in prefix_to_write:
        if key[:len(prefix) + 1] == prefix + ':':
            return True
    return False

def draw_shapes(shapes, overlap, points, x, y, fill, show_missed_tags, tags, 
        processed):
    text_y = 0
    xxx = -(len(shapes) - 1) * 8

    if overlap != 0:
        for shape in shapes:
            has_space = True
            for p in points[-1000:]:
                if x + xxx - overlap <= p.x <= x + xxx + overlap and \
                        y - overlap <= p.y <= y + overlap:
                    has_space = False
                    break
            if has_space:
                draw_point_shape(shape, x + xxx, y, fill)
                points.append(Vector(x + xxx, y))
                xxx += 16
    else:
        for shape in shapes:
            draw_point_shape(shape, x + xxx, y, fill)
            xxx += 16

    if show_missed_tags:
        for k in tags:
            if not no_draw(k) and not k in processed:
                point(k, tags[k], x, y, fill, text_y)
                text_y += 10

def construct_nodes(drawing):
    print 'Draw nodes...'

    start_time = datetime.datetime.now()

    node_number = 0
    processed_tags = 0
    skipped_tags = 0

    s = sorted(node_map.keys(), key=lambda x: -node_map[x]['lat'])

    for node_id in s:
        node_number += 1
        ui.write_line(node_number, len(node_map))
        node = node_map[node_id]
        flinged = flinger.fling(Geo(node['lat'], node['lon']))
        x = flinged.x
        y = flinged.y
        if 'tags' in node:
            tags = node['tags']
        else:
            tags = {}

        shapes, fill, processed = process.get_icon(tags, scheme)

        for k in tags:
            if k in processed or no_draw(k):
                processed_tags += 1
            else:
                skipped_tags += 1

        for k in []:  # tags:
            if to_write(k):
                draw_text(k + ': ' + tags[k], x, y + 18 + text_y, '444444')
                text_y += 10

        #if show_missed_tags:
        #    for k in tags:
        #        v = tags[k]
        #        if not no_draw(k) and not k in processed:
        #            if ('node ' + k + ': ' + v) in missed_tags:
        #                missed_tags['node ' + k + ': ' + v] += 1
        #            else:
        #                missed_tags['node ' + k + ': ' + v] = 1

        if not draw:
            continue

        drawing['nodes'].append({'shapes': shapes, 
            'x': x, 'y': y, 'color': fill, 'processed': processed, 
            'tags': tags})

    ui.write_line(-1, len(node_map))
    print 'Nodes drawed in ' + str(datetime.datetime.now() - start_time) + '.'
    print 'Tags processed: ' + str(processed_tags) + ', tags skipped: ' + \
        str(skipped_tags) + ' (' + \
        str(processed_tags / float(processed_tags + skipped_tags) * 100) + ' %).'

def way_sorter(element):
    if 'layer' in element:
        return element['layer']
    else:
        return 0

def node_sorter(element):
    if 'layer' in element:
        return element['layer']
    else:
        return 0

def draw(drawing, show_missed_tags=False, overlap=14, draw=True):
    ways = sorted(drawing['ways'], key=way_sorter)
    for way in ways:
        draw_path(way['nodes'], way['style'])
    nodes = sorted(drawing['nodes'], key=node_sorter)
    for node in nodes:
        draw_shapes(node['shapes'], overlap, points, node['x'], node['y'], 
            node['color'], show_missed_tags, node['tags'], node['processed'])

# Actions

options = ui.parse_options(sys.argv)

if not options:
    sys.exit(1)

input_file_name = options['input_file_name']

if not os.path.isfile(input_file_name):
    print 'Fatal: no such file: ' + input_file_name + '.'
    sys.exit(1)

node_map, way_map, relation_map = osm_reader.parse_osm_file(input_file_name, 
    parse_ways=options['draw_ways'], parse_relations=False)

output_file = svg.SVG(open(options['output_file_name'], 'w+'))

w, h = 2650, 2650

if 'size' in options:
    w = options['size'][0]
    h = options['size'][1]

output_file.begin(w, h)
output_file.rect(0, 0, w, h, color=background_color)

minimum = Geo(180, 180)
maximum = Geo(-180, -180)

if 'boundary_box' in options:
    bb = options['boundary_box']
    min1 = Geo(bb[2], bb[0])
    max1 = Geo(bb[3], bb[1])

authors = {}
missed_tags = {}
points = []
icons_to_draw = []  # {shape, x, y, priority}

scheme = yaml.load(open(tags_file_name))
scheme['cache'] = {}
w3c_colors = yaml.load(open(colors_file_name))
for color_name in w3c_colors:
    scheme['colors'][color_name] = w3c_colors[color_name]

if len(sys.argv) > 3:
    flinger = GeoFlinger(min1, max1, Vector(0, 0), Vector(w, h))
else:
    print 'Compute borders...'
    minimum, maximum = get_min_max(node_map)
    flinger = GeoFlinger(minimum, maximum, Vector(25, 25), Vector(975, 975))
    print 'Done.'

icons = extract_icon.IconExtractor(icons_file_name)

drawing = {'nodes': [], 'ways': []}

if options['draw_ways']:
    construct_ways(drawing)

construct_nodes(drawing)

draw(drawing, show_missed_tags=options['show_missed_tags'], 
     overlap=options['overlap'], draw=options['draw_nodes'])

if flinger.space.x == 0:
    output_file.rect(0, 0, w, flinger.space.y, color='FFFFFF')
    output_file.rect(0, h - flinger.space.y, w, flinger.space.y, color='FFFFFF')

output_file.end()

top_missed_tags = sorted(missed_tags.keys(), key=lambda x: -missed_tags[x])
missed_tags_file = open(missed_tags_file_name, 'w+')
for tag in top_missed_tags:
    missed_tags_file.write('- {tag: "' + tag + '", count: ' + \
        str(missed_tags[tag]) + '}\n')
missed_tags_file.close()

sys.exit(0)

top_authors = sorted(authors.keys(), key=lambda x: -authors[x])
for author in top_authors:
    print author + ': ' + str(authors[author])
