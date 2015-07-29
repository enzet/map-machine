#!/usr/bin/python
# -*- coding: utf-8 -*- from __future__ import unicode_literals

"""
Simple tool for working with OpenStreetMap data.

Author: Sergey Vartanov (me@enzet.ru).
"""

import datetime
import os
import re
import sys
import xml.dom.minidom

import extract_icon
import osm_reader

from flinger import GeoFlinger, Geo

sys.path.append('lib')

import svg
from vector import Vector

input_file_name = sys.argv[1]

if not os.path.isfile(input_file_name):
    print 'Fatal: no such file: ' + input_file_name + '.'
    sys.exit(1)

#start_time = datetime.datetime.now()
#input_file = open(input_file_name)
#content = xml.dom.minidom.parse(input_file)
#input_file.close()
#print 'File readed in ' + str(datetime.datetime.now() - start_time) + '.'

node_map, way_map, relation_map = osm_reader.parse_osm_file(input_file_name)

output_file = svg.SVG(open(sys.argv[2], 'w+'))

w, h = 2000, 2000

background_color = 'EEEEEE'
grass_color = 'C8DC94'
sand_color = 'F0E0D0'
beach_color = 'F0E0C0'
desert_color = 'F0E0D0'
playground_color = '884400'
parking_color = 'DDCC99'
water_color = 'AACCFF'
water_border_color = '6688BB'
wood_color = 'B8CC84'

tags_to_write = ['operator', 'opening_hours', 'cuisine', 'network',  'website', 
                 'phone', 'branch', 'route_ref', 'brand', 'ref', 'wikipedia', 
                 'description', 'level', 'wikidata', 'name', 'alt_name', 
                 'image', 'fax', 'old_name', 'artist_name', 'int_name',
                 'official_name', 'full_name', 'email', 'designation']

prefix_to_write = ['addr', 'contact', 'name', 'operator', 'wikipedia', 
                   'alt_name', 'description', 'old_name', 'inscription', 
                   'route_ref', 'is_in', 'website']

tags_to_skip = ['note', 'layer', 'source', 'building:part', 'fixme', 'comment']

prefix_to_skip = ['source']

output_file.begin(w, h)
output_file.rect(0, 0, w, h, color=background_color)

minimum = Geo(180, 180)
maximum = Geo(-180, -180)

if len(sys.argv) > 3:
    min1 = Geo(float(sys.argv[5]), float(sys.argv[3]))
    max1 = Geo(float(sys.argv[6]), float(sys.argv[4]))

authors = {}
missed_tags = {}

def get_d_from_file(file_name):
    path, x, y = icons.get_path(file_name)
    if path:
        return path, x, y
    else:
        # print 'No such icon: ' + file_name
        # TODO: add to missed icons
        return 'M 4,4 L 4,10 10,10 10,4 4,4', 0, 0

    # Old style.

    if os.path.isfile('icons/' + file_name + '.svg'):
        file_name = 'icons/' + file_name + '.svg'
        size = 16
    elif os.path.isfile('icons/' + file_name + '.16.svg'):
        file_name = 'icons/' + file_name + '.16.svg'
        size = 16
    elif os.path.isfile('icons/' + file_name + '-12.svg'):
        file_name = 'icons/' + file_name + '-12.svg'
        size = 12
    elif os.path.isfile('icons/' + file_name + '.12.svg'):
        file_name = 'icons/' + file_name + '.12.svg'
        size = 12
    elif os.path.isfile('icons/' + file_name + '.10.svg'):
        file_name = 'icons/' + file_name + '.10.svg'
        size = 10
    else:
        print 'Unknown file:', file_name
        return 'M 4,4 L 4,10 10,10 10,4 4,4', 16
    f = open(file_name).read().split('\n')
    for line in f:
        m = re.match('.* d="(?P<path>[AaMmCcLlZz0-9Ee., -]*)".*', line)
        if m:
            return m.group('path'), size


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


minimum, maximum = get_min_max(node_map)

if len(sys.argv) > 3:
    flinger = GeoFlinger(min1, max1, Vector(0, 0), Vector(w, h))
else:
    flinger = GeoFlinger(minimum, maximum, Vector(25, 25), Vector(975, 975))


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
    output_file.write('<path d="' + shape + \
            '" style="fill:#FFFFFF;opacity:0.5;stroke:#FFFFFF;stroke-width:3;stroke-linejoin:round;" transform="translate(' + \
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
    if ('node ' + k + ': ' + v) in missed_tags:
        missed_tags['node ' + k + ': ' + v] += 1
    else:
        missed_tags['node ' + k + ': ' + v] = 1
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
        if not (int(way['tags']['layer']) in layers):
            layers[int(way['tags']['layer'])] = \
                {'b': [], 'h1': [], 'h2': [], 'r': [], 'n': [], 'l': [],
                 'a': [], 'le': [], 'ba': [], 'bo': [], 'w': []}
        layer = layers[int(way['tags']['layer'])]
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


layers = construct_layers()

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


def draw_ways():
    for level in sorted(layers.keys()):
        layer = layers[level]
        #for entity in ['b', 'h1', 'h2', 'r', 'n', 'l', 'a', 'le', 'ba']:

        # Pre part.

        for way in layer['le']:
            if way['tags']['leisure'] == 'park':
                style = 'fill:#' + grass_color + ';'
            else:
                continue
            draw_path(way['nodes'], style)

        # Post part.

        for way in layer['l']:
            text_y = 0
            c = line_center(way['nodes'])
            if way['tags']['landuse'] == 'grass':
                style = 'fill:#' + grass_color + ';stroke:none;'
                draw_path(way['nodes'], style)
            elif way['tags']['landuse'] == 'conservation':
                style = 'fill:#' + grass_color + ';stroke:none;'
                draw_path(way['nodes'], style)
            elif way['tags']['landuse'] == 'forest':
                style = 'fill:#' + wood_color + ';stroke:none;'
                draw_path(way['nodes'], style)
            elif way['tags']['landuse'] == 'garages':
                style = 'fill:#' + parking_color + ';stroke:none;'
                draw_path(way['nodes'], style)
                draw_point_shape('parking', c.x, c.y, '444444')
            elif way['tags']['landuse'] in ['residential', 'commercial']:
                continue
            else:
                style = 'fill:#0000FF;stroke:none;'
                draw_path(way['nodes'], style)
            #for tag in way['tags']:
            #    if not (tag in ['landuse', 'layer']):
            #        point(tag, str(way['tags'][tag]), c.x, c.y, '000000', text_y)
            #        text_y += 10
        for way in layer['a']:
            c = line_center(way['nodes'])
            if way['tags']['amenity'] == 'parking':
                style = 'fill:#' + parking_color + ';stroke:none;'
                draw_path(way['nodes'], style)
                draw_point_shape('parking', c.x, c.y, '444444')
            elif way['tags']['amenity'] == 'school':
                continue
            else:
                style = 'fill:#0000FF;stroke:none;'
                draw_path(way['nodes'], style)
        for way in layer['n']:
            if way['tags']['natural'] == 'wood':
                style = 'fill:#' + wood_color + ';stroke:none;'
            elif way['tags']['natural'] == 'scrub':
                style = 'fill:#' + wood_color + ';stroke:none;'
            elif way['tags']['natural'] == 'sand':
                style = 'fill:#' + sand_color + ';stroke:none;'
            elif way['tags']['natural'] == 'beach':
                style = 'fill:#' + beach_color + ';stroke:none;'
            elif way['tags']['natural'] == 'desert':
                style = 'fill:#' + desert_color + ';stroke:none;'
            elif way['tags']['natural'] == 'water':
                style = 'fill:#' + water_color + ';stroke:#' + water_border_color + ';stroke-width:1.0;'
            elif way['tags']['natural'] == 'forest':
                style = 'fill:#' + wood_color + ';stroke:none;'
            else:
                continue
            draw_path(way['nodes'], style)
        for way in layer['w']:
            if way['tags']['waterway'] == 'riverbank':
                style = 'fill:#' + water_color + ';stroke:#' + water_border_color + ';stroke-width:1.0;'
            elif way['tags']['waterway'] == 'river':
                style = 'fill:none;stroke:#' + water_color + ';stroke-width:10.0;'
            draw_path(way['nodes'], style)
        for way in layer['r']:
            v = way['tags']['railway']
            style = 'fill:none;stroke-dasharray:none;stroke-linejoin:round;stroke-linecap:round;stroke-width:'
            if v == 'subway': style += '10;stroke:#DDDDDD;'
            if v in ['narrow_gauge', 'tram']: 
                style += '2;stroke:#000000;'
            else:
                continue
            draw_path(way['nodes'], style)
        for way in layer['h1']:
            if 'tunnel' in way['tags'] and way['tags']['tunnel'] == 'yes':
                style = 'fill:none;stroke:#FFFFFF;stroke-dasharray:none;stroke-linejoin:round;stroke-linecap:round;stroke-width:10;'
                draw_path(way['nodes'], style)
        for way in layer['h1']:
            v = way['tags']['highway']
            style = 'fill:none;stroke:#AAAAAA;stroke-dasharray:none;stroke-linejoin:round;stroke-linecap:round;stroke-width:'
            if v == 'motorway': style += '30'
            elif v == 'trunk': style += '25'
            elif v == 'primary': style += '20;stroke:#AA8800'
            elif v == 'secondary': style += '13'
            elif v == 'tertiary': style += '11'
            elif v == 'unclassified': style += '9'
            elif v == 'residential': style += '8'
            elif v == 'service': style += '7'
            elif v == 'track': style += '3'
            elif v in ['footway', 'pedestrian']: style += '2'
            elif v == 'steps': style += '5;stroke-dasharray:1,2;stroke-linecap:butt'
            elif v == 'path': style += '1;stroke-dasharray:5,5;stroke-linecap:round'
            else:
                continue
            style += ';'
            draw_path(way['nodes'], style)
        for way in layer['h2']:
            v = way['tags']['highway']
            style = 'fill:none;stroke:#FFFFFF;stroke-linecap:round;stroke-linejoin:round;stroke-width:'
            if v == 'motorway': style += '28'
            elif v == 'trunk': style += '23'
            elif v == 'primary': style += '19;stroke:#FFDD66'
            elif v == 'secondary': style += '11'
            elif v == 'tertiary': style += '9'
            elif v == 'unclassified': style += '7'
            elif v == 'residential': style += '6'
            elif v == 'service': style += '5'
            else:
                continue
            style += ';'
            draw_path(way['nodes'], style)
        for way in layer['b']:
            floors = 0
            text_y = 0
            #if 'building:levels' in way['tags']:
                #floors = float(way['tags']['building:levels'])
            draw_path(way['nodes'], 'fill:#D0D0C0;stroke:#AAAAAA;opacity:1.0;')
            c = line_center(way['nodes'])
            for tag in way['tags']:
                v = way['tags'][tag]
                if tag == 'building':
                    if v == 'yes':
                        pass
                    elif v == 'apartments':
                        draw_point_shape('apartments', c.x, c.y, '444444')
                    elif v == 'kindergarten':
                        draw_point_shape('playground', c.x, c.y, '444444')
                elif tag == 'amenity':
                    if v == 'cafe':
                        draw_point_shape('cafe', c.x, c.y, '444444')
                    elif v == 'theatre':
                        draw_point_shape('theatre', c.x, c.y, '444444')
                    elif v == 'fast_food':
                        draw_point_shape('fast_food', c.x, c.y, '444444')
                    elif v == 'snack_cart':
                        draw_point_shape('cafe', c.x, c.y, '444444')
                elif tag == 'shop':
                    if v == 'clothes':
                        draw_point_shape('shop_clothes', c.x, c.y, '444444')
                    elif v == 'gift':
                        draw_point_shape('shop_gift', c.x, c.y, '444444')
                elif tag == 'power':
                    draw_point_shape('electricity', c.x, c.y, '444444')
                #elif tag in ['name', 'addr:housenumber', 'cladr:code', 
                #             'addr:city', 'addr:street', 'website',
                #             'wikidata'] or \
                #        'name' in tag or 'wikipedia' in tag:
                #    draw_text(v, str(c.x), str(c.y + 18 + text_y), '444444')
                #    text_y += 10
                #elif tag == 'addr:country':
                #    if v == 'RU':
                #        draw_text('Россия', str(c.x), str(c.y + 18 + text_y), '444444')
                #    else:
                #        draw_text(v, str(c.x), str(c.y + 18 + text_y), '444444')
                #    text_y += 10
                elif tag in ['layer', 'height']:
                    pass
                elif tag in ['building:levels']:
                    pass
                else:
                    kk = tag
                    vv = v
                    if ('way ' + kk + ': ' + vv) in missed_tags:
                        missed_tags['way ' + kk + ': ' + vv] += 1
                    else:
                        missed_tags['way ' + kk + ': ' + vv] = 1
        for way in layer['le']:
            c = line_center(way['nodes'])
            if way['tags']['leisure'] == 'playground':
                style = 'fill:#' + playground_color + ';opacity:0.2;'
                draw_point_shape('playground', c.x, c.y, '444444')
            elif way['tags']['leisure'] == 'garden':
                style = 'fill:#' + grass_color + ';'
            elif way['tags']['leisure'] == 'pitch':
                style = 'fill:#' + playground_color + ';opacity:0.2;'
            elif way['tags']['leisure'] == 'park':
                continue
            else:
                style = 'fill:#FF0000;opacity:0.2;'
            draw_path(way['nodes'], style)
        for way in layer['ba']:
            if way['tags']['barrier'] == 'hedge':
                style += 'fill:none;stroke:#' + wood_color + ';stroke-width:4;'
            else:
                style += 'fill:none;stroke:#000000;stroke-width:1;opacity:0.4;'
            draw_path(way['nodes'], style)
        for way in layer['bo']:
            style += 'fill:none;stroke:#FF0000;stroke-width:0.5;stroke-dahsarray:10,20;'
            draw_path(way['nodes'], style)

print 'Done.'

# Nodes drawing

def draw_raw_nodes():
    for node_id in node_map:
        node = node_map[node_id]
        flinged = flinger.fling(node)
        output_file.circle(flinged.x, flinged.y, 0.2, color='FFFFFF')

def no_draw(key):
    if key in tags_to_write or key in tags_to_skip:
        return True
    for prefix in prefix_to_write + prefix_to_skip:
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

def draw_nodes():
    print 'Draw nodes...'

    for node_id in node_map:
        node = node_map[node_id]
        flinged = flinger.fling(Geo(node['lat'], node['lon']))
        x = flinged.x
        y = flinged.y
        text_y = 0
        if 'tags' in node:
            p = node['tags']
        else:
            p = {}
        fill = '444444'
        processed = set([])

        if 'colour' in p or 'color' in p:
            k = 'color' if 'color' in p else 'colour'
            v = p[k]
            processed.add(k)
            if v == 'blue':
                fill='2233AA'
            elif v == 'lightblue':
                fill='2288CC'
            elif v == 'red':
                fill='CC0000'
            elif v == 'violet':
                fill='75507B'
            elif v == 'green':
                fill='4E9A06'
            elif v == 'yellow':
                fill='EDD400'
            else:
                processed.remove(k)

        shapes = []

        if p == {}:
            pass
        elif 'amenity' in p:
            k = 'amenity'
            v = p['amenity']
            processed.add(k)
            if v in ['bench', 'bicycle_parking', 'cafe', 'waste_basket', 
                     'clinic', 'restaurant', 'pharmacy', 'drinking_water', 
                     'toilets', 'theatre', 'bar', 'bank', 'pub', 'post_office']:
                shapes.append(v)
            elif v == 'fast_food':
                shape = 'fast_food'
                if 'operator' in p:
                    if p['operator'] == "McDonald's":
                        shape = 'mcdonalds'
                        processed.add('operator')
                if 'operator:en' in p:
                    if p['operator:en'] == "McDonald's":
                        shape = 'mcdonalds'
                        processed.add('operator:en')
                shapes.append(shape)
            elif v == 'shop':
                if 'shop' in p:
                    if p['shop'] in ['fishing']:
                        draw_point_shape('shop_' + p['shop'], x, y, fill)
            elif v == 'fountain':
                shapes.append('fountain')
                fill = water_border_color
            elif v == 'recycling':
                if not 'recycling_type' in p:
                    shapes.append('recycling')
            else:
                processed.remove(k)
            for k in p:
                if 'karaoke' in p and p['karaoke'] == 'yes':
                    draw_point_shape('microphone', flinged.x + 16, y, fill)
                    processed.add('karaoke')
        elif 'building' in p:
            k = 'building'
            v = p['building']
            for k in p:
                if 'roof:material' in p and p['roof:material'] == 'metal':
                    draw_point_shape('metal_roof', flinged.x + 16, y, fill)
                    processed.add('roof:material')
        elif 'railway' in p:
            k = 'railway'
            v = p['railway']
            processed.add(k)
            if v == 'subway_entrance':
                shapes.append('train')
            else:
                processed.remove(k)
            for k in p:
                if 'roof:material' in p and p['roof:material'] == 'metal':
                    draw_point_shape('metal_roof', flinged.x + 16, y, fill)
                    processed.add('roof:material')
        elif 'natural' in p:
            k = 'natural'
            v = p['natural']
            processed.add(k)
            if v == 'tree':
                shape = 'tree'
                if 'leaf_type' in p and p['leaf_type'] in ['broadleaved', 'needleleaved']:
                    shape = p['leaf_type']
                    processed.add('leaf_type')
                if 'type' in p and p['type'] == 'conifer':
                    shape = 'needleleaved'
                    processed.add('type')
                if 'denotation' in p:
                    if p['denotation'] == 'urban':
                        draw_point_shape([shape, 'urban_tree_pot'], x, y, wood_color)
                        processed.add('denotation')
                    elif p['denotation'] == 'avenue':
                        draw_point_shape([shape, 'avenue_tree'], x, y, wood_color)
                        processed.add('denotation')
            elif v == 'cave_entrance':
                shapes.append('cave')
            elif v == 'bush':
                shapes.append('bush')
                fill = wood_color
            else:
                processed.remove(k)
        elif 'entrance' in p:
            k = 'entrance'
            v = p['entrance']
            processed.add(k)
            if v == 'yes':
                shapes.append('entrance')
            elif v == 'main':
                shapes.append('main_entrance')
            elif v == 'staircase':
                shapes.append('staircase')
            else:
                processed.remove(k)
        elif 'highway' in p:
            k = 'highway'
            v = p['highway']
            processed.add(k)
            if v == 'crossing':
                shape = 'crossing'
                if 'crossing' in p:
                    if p['crossing'] == 'zebra':
                        shape = 'zebra'
                        processed.add('crossing')
                    elif p['crossing'] == 'uncontrolled':
                        draw_point_shape('no_traffic_signals', x + 16, y, fill)
                        processed.add('crossing')
                    elif p['crossing'] == 'traffic_signals':
                        draw_point_shape('traffic_signals', x + 16, y, fill)
                        processed.add('crossing')
                elif 'crossing_ref' in p:
                    if p['crossing_ref'] == 'zebra':
                        shape = 'zebra'
                        processed.add('crossing_ref')
                shapes.append(shape)
            elif v == 'traffic_signals':
                shapes.append('traffic_signals')
            elif v == 'street_lamp':
                shapes.append('street_lamp')
            else:
                processed.remove(k)
        elif 'historic' in p:
            k = 'historic'
            v = p['historic']
            processed.add(k)
            if v == 'memorial':
                shape = v
                if v in p:
                    if p[v] == 'statue':
                        shape = p[v]
                        processed.add(v)
                    elif p[v] == 'plaque':
                        shape = p[v]
                        processed.add(v)
                shapes.append(shape)
            elif v == 'tomb':
                shape = v
                if v in p:
                    if p[v] == 'mausoleum':
                        shape = p[v]
                        processed.add(v)
                shapes.append(shape)
            else:
                processed.remove(k)
        elif 'barrier' in p:
            k = 'barrier'
            v = p['barrier']
            processed.add(k)
            if v == 'gate':
                shapes.append('gate')
            elif v == 'lift_gate':
                shapes.append('lift_gate')
            elif v == 'turnstile':
                shapes.append('turnstile')
            else:
                processed.remove(k)
        elif 'man_made' in p:
            k = 'man_made'
            v = p['man_made']
            processed.add(k)
            if v == 'pole':
                shapes.append('pole')
            elif v == 'flagpole':
                shapes.append('flagpole')
            else:
                processed.remove(k)
        elif 'tourism' in p:
            k = 'tourism'
            v = p['tourism']
            processed.add(k)
            if v == 'attraction':
                shape = v
                if v in p:
                    if p[v] == 'amusement_ride':
                        shape = p[v]
                        processed.add(v)
                shapes.append(shape)
            else:
                processed.remove(k)

        for k in []:  # p:
            if to_write(k):
                draw_text(k + ': ' + p[k], x, y + 18 + text_y, '444444')
                text_y += 10

        for k in p:
            if k == 'foot' and p[k] == 'yes':
                shapes.append('foot')
                processed.add(k)
            elif k == 'bicycle' and p[k] == 'yes':
                shapes.append('bicycle')
                processed.add(k)
            elif k == 'internet_access' and p[k] == 'wlan':
                shapes.append('wlan')
                processed.add(k)
            elif not no_draw(k) and not k in processed:
                point(k, p[k], x, y, fill, text_y)
                text_y += 10
            
        xxx = -(len(shapes) - 1) * 8
        for shape in shapes:
            draw_point_shape(shape, x + xxx, y, fill)
            xxx += 16

print 'Done.'

#draw_raw_nodes()
#draw_raw_ways()

text_y = 0

icons = extract_icon.IconExtractor('icons.svg')

#sys.exit(0)

draw_ways()
draw_nodes()

if flinger.space.x == 0:
    output_file.rect(0, 0, w, flinger.space.y, color='FFFFFF')
    output_file.rect(0, h - flinger.space.y, w, flinger.space.y, color='FFFFFF')

output_file.end()

print '\nMissing tags:\n'
top_missed_tags = reversed(sorted(missed_tags.keys(), key=lambda x: -missed_tags[x]))
for tag in top_missed_tags:
    if tag[:4] == 'node':
        print tag + ' (' + str(missed_tags[tag]) + ')'

sys.exit(0)

top_authors = sorted(authors.keys(), key=lambda x: -authors[x])
for author in top_authors:
    print author + ': ' + str(authors[author])
