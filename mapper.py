#!/usr/bin/python
# -*- coding: utf-8 -*- from __future__ import unicode_literals

# Author: Sergey Vartnov

import os
import re
import sys
import xml.dom.minidom

from flinger import GeoFlinger, Geo

sys.path.append('lib')

import svg
from vector import Vector

# class OSMGetter:
#     def get(x1, x2, y1, y2):
#         input_file = open(cache_folder + '/osm-' + `x1` + '-' + `y1` + '-' + \
#             `x2` + '-' + `y2`
#         if not os.path.isfile(input_file):

input_file_name = sys.argv[1]

if not os.path.isfile(input_file_name):
    sys.exit(1)

print 'Reading input OSM file...'

input_file = open(input_file_name)
content = xml.dom.minidom.parse(input_file)
input_file.close()

print 'Done.'

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

output_file.begin(w, h)
output_file.rect(0, 0, w, h, color=background_color)

minimum = Geo(180, 180)
maximum = Geo(-180, -180)

if len(sys.argv) > 3:
    min1 = Geo(float(sys.argv[5]), float(sys.argv[3]))
    max1 = Geo(float(sys.argv[6]), float(sys.argv[4]))

authors = {}
missed_tags = {}

d_street_lamp = 'm 7,1 -3.5,3 1.59375,0 1,5 1.40625,0 0,6 1,0 0,-6 1.40625,0 1,-5 L 12.5,4 9,1 z M 6.125,4 9.875,4 9.09375,8 6.90625,8 z'
d_clinic = 'M 7,5 7,7 5,7 5,9 7,9 7,11 9,11 9,9 11,9 11,7 9,7 9,5 7,5'
d_crossing = 'm 3,5 0,6 1,0 0,-6 z m 4,0 0,6 1,0 0,-6 z m 4,0 0,6 1,0 0,-6 z'
d_traffic_signal = 'M 7,1 C 6.446,1 6,1.446 6,2 L 6,4 C 6,4.1879013 6.0668244,4.3501348 6.15625,4.5 6.0668244,4.6498652 6,4.8120987 6,5 L 6,7 C 6,7.1879013 6.0668244,7.3501348 6.15625,7.5 6.0668244,7.6498652 6,7.8120987 6,8 l 0,2 c 0,0.554 0.446,1 1,1 l 0.5,0 0,3 -1.5,0 0,1 4,0 0,-1 -1.5,0 0,-3 0.5,0 c 0.554,0 1,-0.446 1,-1 L 10,8 C 10,7.8120987 9.9331756,7.6498652 9.84375,7.5 9.9331756,7.3501348 10,7.1879013 10,7 L 10,5 C 10,4.8120987 9.9331756,4.6498652 9.84375,4.5 9.9331756,4.3501348 10,4.1879013 10,4 L 10,2 C 10,1.446 9.554,1 9,1 z M 7,2 9,2 9,4 7,4 z M 7,5 9,5 9,7 7,7 z m 0,3 2,0 0,2 -2,0 z'
d_tree = 'M 7 2 C 6.446 2 6 2.446 6 3 C 5.446 3 5 3.4460001 5 4 L 5 7 C 5 7.5539999 5.446 8 6 8 C 6 8.554 6.446 9 7 9 L 7.5625 9 L 7.5625 12 L 8.4375 12 L 8.4375 9 L 9 9 C 9.554 9 10 8.554 10 8 C 10.554 8 11 7.5539999 11 7 L 11 4 C 11 3.4460001 10.554 3 10 3 C 10 2.446 9.554 2 9 2 L 7 2 z'

def get_d_from_file(file_name):
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

# Construct node map

def construct_node_map():
    """
    Construct map of nodes.
    """
    print 'Construct node map...'
    node_map = {}
    for element in content.childNodes[0].childNodes:
        if element.nodeType != element.TEXT_NODE:
            if 'user' in element.attributes.keys():
                author = element.attributes['user'].value
                if author in authors:
                    authors[author] += 1
                else:
                    authors[author] = 1
            if not ('lat' in element.attributes.keys()):
                continue
            node_map[element.attributes['id'].value] = \
                Geo(float(element.attributes['lat'].value), 
                    float(element.attributes['lon'].value))
            if float(element.attributes['lat'].value) > maximum.lat: 
                maximum.lat = float(element.attributes['lat'].value)
            if float(element.attributes['lat'].value) < minimum.lat: 
                minimum.lat = float(element.attributes['lat'].value)
            if float(element.attributes['lon'].value) > maximum.lon: 
                maximum.lon = float(element.attributes['lon'].value)
            if float(element.attributes['lon'].value) < minimum.lon: 
                minimum.lon = float(element.attributes['lon'].value)
    print 'Done.'
    return node_map

node_map = construct_node_map()

if len(sys.argv) > 3:
    flinger = GeoFlinger(min1, max1, Vector(0, 0), Vector(w, h))
else:
    flinger = GeoFlinger(minimum, maximum, Vector(25, 25), Vector(975, 975))


def draw_path(nodes, style, shift=Vector()):
    prev_node = None
    for node_id in nodes:
        flinged1 = flinger.fling(node_map[node_id]) + shift
        if prev_node:
            flinged2 = flinger.fling(prev_node) + shift
            output_file.write('L ' + `flinged1.x` + ',' + `flinged1.y` + ' ')
        else:
            output_file.write('<path d="M ' + `flinged1.x` + \
                ',' + `flinged1.y` + ' ')
        prev_node = node_map[node_id]
    output_file.write('" style="' + style + '" />\n')

def draw_point_shape(name, x, y, fill):
    shape, size = get_d_from_file(name)
    draw_point(shape, x, y, fill, size=size)

def draw_point(shape, x, y, fill, size=16):
    x = int(float(x))
    y = int(float(y))
    output_file.write('<path d="' + shape + \
            '" style="fill:#FFFFFF;opacity:0.5;stroke:#FFFFFF;stroke-width:3;stroke-linejoin:round;" transform="translate(' + \
         str(x - size / 2.0) + ',' + str(y - size / 2.0) + ')" />\n')
    output_file.write('<path d="' + shape + \
         '" style="fill:#' + fill + ';fill-opacity:1" transform="translate(' + \
         str(x - size / 2.0) + ',' + str(y - size / 2.0) + ')" />\n')

def draw_text(text, x, y, fill):
    if type(text) == unicode:
        text = text.encode('utf-8')
    text = text.replace('&', 'and')
    if text[:7] == 'http://' or text[:8] == 'https://':
        text = 'link'
        fill = '0000FF'
    return
    output_file.write('<text x="' + x + '" y="' + y + \
            '" style="font-size:10;text-anchor:middle;font-family:Myriad Pro;fill:#FFFFFF;stroke-linejoin:round;stroke-width:5;stroke:#FFFFFF;opacity:0.5;">' + text + '</text>')
    output_file.write('<text x="' + x + '" y="' + y + \
            '" style="font-size:10;text-anchor:middle;font-family:Myriad Pro;fill:#' + fill + ';">' + text + '</text>')

def point(k, v, x, y, fill):
    if ('node ' + k + ': ' + v) in missed_tags:
        missed_tags['node ' + k + ': ' + v] += 1
    else:
        missed_tags['node ' + k + ': ' + v] = 1
    output_file.circle(x, y, 2, fill=fill, color=fill)
    text = k + ': ' + v
    if type(text) == unicode:
        text = text.encode('utf-8')
    output_file.write('<text x="' + str(x) + '" y="' + str(int(y) + 10) + \
            '" style="font-size:10;text-anchor:middle;font-family:Myriad Pro;fill:#FF0000;">' + text + '</text>')

# Ways drawing

def construct_way_map():
    """
    Construct map of ways and distribute them by layers. One layer may contain
    elements of different types.
    """
    print 'Construct way map...'

    layers = {}
    way_map = {}

    for element in content.childNodes[0].childNodes:
        if element.nodeName == 'way':
            way = {'nodes': [], 'tags': {}}
            way_map[element.attributes['id'].value] = way

    for element in content.childNodes[0].childNodes:
        if element.nodeName == 'relation':
            relation = {'members': [], 'tags': {}}
            for child_node in element.childNodes:
                if isinstance(child_node, xml.dom.minidom.Element):
                    if child_node.tagName == 'tag':
                        k = child_node.attributes['k'].value
                        v = child_node.attributes['v'].value
                        relation['tags'][k] = v
            for child_node in element.childNodes:
                if isinstance(child_node, xml.dom.minidom.Element):
                    if child_node.tagName == 'member':
                        index = child_node.attributes['ref'].value
                        if index in way_map:
                            way = way_map[index]
                            for tag in relation['tags']:
                                way['tags'][tag] = relation['tags'][tag]

    for element in content.childNodes[0].childNodes:
        if element.nodeName == 'way':
            way = way_map[element.attributes['id'].value]
            for child_node in element.childNodes:
                if isinstance(child_node, xml.dom.minidom.Element):
                    if child_node.tagName == 'tag':
                        k = child_node.attributes['k'].value
                        v = child_node.attributes['v'].value
                        way['tags'][k] = v
                    if child_node.tagName == 'nd':
                        way['nodes'].append(child_node.attributes['ref'].value)
            if not ('layer' in way['tags']):
                way['tags']['layer'] = 0
            if not (int(way['tags']['layer']) in layers):
                layers[int(way['tags']['layer'])] = \
                    {'b': [], 'h1': [], 'h2': [], 'r': [], 'n': [], 'l': [],
                     'a': [], 'le': [], 'ba': [], 'bo': []}
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
            #else:
            #    empty = True
            #    for key in way['tags'].keys():
            #        if not (key in ['layer', 'note']):
            #            empty = False
            #    if not empty:
            #        print 'Unknown kind of way:', way['tags']
    return layers, way_map


layers, way_map = construct_way_map()

def draw_raw_ways():
    for way_id in way_map:
        way = way_map[way_id]
        draw_path(way['nodes'], 'stroke:#FFFFFF;fill:none;stroke-width:0.2;')

def draw_ways():
    for level in sorted(layers.keys()):
        layer = layers[level]
        #for entity in ['b', 'h1', 'h2', 'r', 'n', 'l', 'a', 'le', 'ba']:
        for way in layer['le']:
            if way['tags']['leisure'] == 'park':
                style = 'fill:#' + grass_color + ';'
            else:
                continue
            draw_path(way['nodes'], style)
        for way in layer['l']:
            ma = Vector()
            mi = Vector(10000, 10000)
            for node_id in way['nodes']:
                node = node_map[node_id]
                flinged = flinger.fling(node)
                if flinged.x > ma.x: ma.x = flinged.x
                if flinged.y > ma.y: ma.y = flinged.y
                if flinged.x < mi.x: mi.x = flinged.x
                if flinged.y < mi.y: mi.y = flinged.y
            c = Vector((ma.x + mi.x) / 2.0, (ma.y + mi.y) / 2.0)
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
        for way in layer['a']:
            ma = Vector()
            mi = Vector(10000, 10000)
            for node_id in way['nodes']:
                node = node_map[node_id]
                flinged = flinger.fling(node)
                if flinged.x > ma.x: ma.x = flinged.x
                if flinged.y > ma.y: ma.y = flinged.y
                if flinged.x < mi.x: mi.x = flinged.x
                if flinged.y < mi.y: mi.y = flinged.y
            c = Vector((ma.x + mi.x) / 2.0, (ma.y + mi.y) / 2.0)
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
        for way in layer['r']:
            v = way['tags']['railway']
            style = 'fill:none;stroke-dasharray:none;stroke-linejoin:round;stroke-linecap:butt;stroke-width:'
            if v == 'subway': style += '10;stroke:#DDDDDD;'
            if v in ['narrow_gauge', 'tram']: 
                style += '2;stroke:#000000;'
            else:
                continue
            draw_path(way['nodes'], style)
        for way in layer['h1']:
            if 'tunnel' in way['tags'] and way['tags']['tunnel'] == 'yes':
                style = 'fill:none;stroke:#FFFFFF;stroke-dasharray:none;stroke-linejoin:round;stroke-linecap:butt;stroke-width:10;'
                draw_path(way['nodes'], style)
        for way in layer['h1']:
            v = way['tags']['highway']
            style = 'fill:none;stroke:#AAAAAA;stroke-dasharray:none;stroke-linejoin:round;stroke-linecap:butt;stroke-width:'
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
            elif v == 'path': style += '1;stroke-dasharray:5,5;stroke-linecap:butt'
            else:
                continue
            style += ';'
            draw_path(way['nodes'], style)
        for way in layer['h2']:
            v = way['tags']['highway']
            style = 'fill:none;stroke:#FFFFFF;stroke-linecap:butt;stroke-linejoin:round;stroke-width:'
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
            ma = Vector()
            mi = Vector(10000, 10000)
            for node_id in way['nodes']:
                node = node_map[node_id]
                flinged = flinger.fling(node)
                if flinged.x > ma.x: ma.x = flinged.x
                if flinged.y > ma.y: ma.y = flinged.y
                if flinged.x < mi.x: mi.x = flinged.x
                if flinged.y < mi.y: mi.y = flinged.y
            c = Vector((ma.x + mi.x) / 2.0, (ma.y + mi.y) / 2.0)
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
                elif tag in ['name', 'addr:housenumber', 'cladr:code', 
                             'addr:city', 'addr:street', 'website',
                             'wikidata'] or \
                        'name' in tag or 'wikipedia' in tag:
                    draw_text(v, str(c.x), str(c.y + 18 + text_y), '444444')
                    text_y += 10
                elif tag == 'addr:country':
                    if v == 'RU':
                        draw_text('Россия', str(c.x), str(c.y + 18 + text_y), '444444')
                    else:
                        draw_text(v, str(c.x), str(c.y + 18 + text_y), '444444')
                    text_y += 10
                elif tag in ['layer', 'height']:
                    pass
                elif tag in ['building:levels']:
                    pass
                else:
                    kk = tag
                    vv = unicode(v)
                    if ('way ' + kk + ': ' + vv) in missed_tags:
                        missed_tags['way ' + kk + ': ' + vv] += 1
                    else:
                        missed_tags['way ' + kk + ': ' + vv] = 1
        for way in layer['le']:
            ma = Vector()
            mi = Vector(10000, 10000)
            for node_id in way['nodes']:
                node = node_map[node_id]
                flinged = flinger.fling(node)
                if flinged.x > ma.x: ma.x = flinged.x
                if flinged.y > ma.y: ma.y = flinged.y
                if flinged.x < mi.x: mi.x = flinged.x
                if flinged.y < mi.y: mi.y = flinged.y
            c = Vector((ma.x + mi.x) / 2.0, (ma.y + mi.y) / 2.0)
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

def draw_nodes():
    print 'Draw nodes...'

    for element in content.childNodes[0].childNodes:
        if element.nodeName != 'node':
            continue
        flinged = flinger.fling(Geo(float(element.attributes['lat'].value), 
                                    float(element.attributes['lon'].value)))
        text_y = 0
        pairs = {}
        for child_node in element.childNodes:
            if isinstance(child_node, xml.dom.minidom.Element):
                if child_node.tagName == 'tag':
                    pairs[child_node.attributes['k'].value] = child_node.attributes['v'].value
        fill = '444444'
        if 'colour' in pairs:
            if pairs['colour'] == 'blue':
                fill='2233AA'
                radius=3
        for k in pairs:
            v = pairs[k]
            x = `flinged.x`
            y = `flinged.y`
            if k == 'amenity':
                if v in ['bench', 'bicycle_parking', 'waste_basket', 
                         'restaurant', 'pharmacy', 'drinking_water', 'toilets',
                         'fast_food', 'theatre']:
                    draw_point_shape(v, x, y, fill)
                elif v == 'clinic':
                    draw_point(d_clinic, x, y, fill)
                elif v == 'fountain':
                    draw_point_shape('fountain', x, y, water_border_color)
                elif v == 'recycling':
                    if not 'recycling_type' in pairs:
                        draw_point_shape('recycling', x, y, fill)
                else:
                    point(k, v, flinged.x, flinged.y, fill)
            elif k == 'artwork_type':
                if v == 'statue':
                    draw_point_shape('monument', x, y, fill)
                if v == 'sculpture':
                    draw_point_shape('monument', x, y, fill)
                else:
                    point(k, v, flinged.x, flinged.y, fill)
            elif k == 'barrier':
                if v == 'lift_gate':
                    draw_point_shape('liftgate', x, y, fill)
            elif k in ['crossing', 'crossing_ref']:
                if v == 'zebra':
                    draw_point(d_crossing, x, y, fill)
            elif k == 'entrance':
                draw_point_shape('entrance', x, y, fill)
            elif k == 'highway':
                if v == 'street_lamp': 
                    draw_point(d_street_lamp, x, y, fill)
                elif v == 'bus_stop': 
                    draw_point_shape('bus_stop', x, y, fill)
                elif v == 'traffic_signals': 
                    draw_point(d_traffic_signal, x, y, fill)
                elif v == 'crossing':    
                    if not ('crossing' in pairs):
                        draw_point(d_crossing, x, y, fill)
                else:
                    point(k, v, flinged.x, flinged.y, fill)
            elif k == 'man_made':
                if v == 'pole':
                    draw_point_shape('pole', x, y, fill)
                elif v == 'flagpole':
                    draw_point_shape('flagpole', x, y, fill)
                else:
                    point(k, v, flinged.x, flinged.y, fill)
            elif k == 'natural':
                if v == 'tree':
                    if 'denotation' in pairs and pairs['denotation'] == 'urban':
                        draw_point_shape('urban_tree', x, y, wood_color)
                    else:
                        draw_point(d_tree, x, y, wood_color)
                elif v == 'cave_entrance':
                    draw_point_shape('cave', x, y, fill)
                elif v == 'bush':
                    draw_point_shape('bush', x, y, wood_color)
                else:
                    point(k, v, flinged.x, flinged.y, fill)
            elif k == 'recycling_type':
                if v == 'centre':
                    draw_point_shape('recycling', x, y, fill)
                else:
                    draw_point_shape('recycling', x, y, fill)
            elif k == 'shop':
                if v == 'florist':
                    draw_point_shape('florist', x, y, fill)
                elif v in ['clothes', 'shoes', 'gift']:
                    draw_point_shape('shop_' + v, x, y, fill)
                else:
                    point(k, v, flinged.x, flinged.y, fill)
            elif k == 'traffic_calming':
                if v == 'bump':
                    draw_point_shape('bump', x, y, fill)
                else:
                    point(k, v, flinged.x, flinged.y, fill)
            elif k == 'emergency':
                if v == 'fire_hydrant':
                    draw_point_shape(v, x, y, fill)
            elif k == 'historic':
                if v == 'memorial':
                    draw_point_shape('monument', x, y, fill)
            elif k == 'tourism':
                if v == 'artwork':
                    if not ('artwork_type' in pairs):
                        draw_point_shape('monument', x, y, fill)
                if v == 'attraction':
                    draw_point_shape('monument', x, y, fill)
            elif k in [
                    'operator', 'contact:facebook', 'contact:phone',
                    'opening_hours', 'cuisine', 'network',  'website',
                    'contact:website', 'phone', 'branch', 'route_ref',
                    'addr:flats', 'brand', 'ref', 'addr:street', 'wikipedia',
                    ] or ('name' in k):
                if k == 'route_ref':
                    v = v.replace(';', ' ')
                draw_text(v, x, str(flinged.y + 18 + text_y), fill)
                text_y += 10
            elif k in ['layer', 'level', 'source', 'note', 'description']:
                pass  # NOTHING TO DRAW
            else:
                point(k, v, flinged.x, flinged.y, fill)

print 'Done.'

#draw_raw_nodes()
#draw_raw_ways()

draw_ways()
draw_nodes()

if flinger.space.x == 0:
    output_file.rect(0, 0, w, flinger.space.y, color='FFFFFF')
    output_file.rect(0, h - flinger.space.y, w, flinger.space.y, color='FFFFFF')

output_file.end()

print '\nMissing tags:\n'
top_missed_tags = reversed(sorted(missed_tags.keys(), key=lambda x: -missed_tags[x]))
for tag in top_missed_tags:
    print tag + ' (' + str(missed_tags[tag]) + ')'

sys.exit(1)

top_authors = sorted(authors.keys(), key=lambda x: -authors[x])
for author in top_authors:
    print author + ': ' + str(authors[author])
