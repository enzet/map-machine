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

undraw = ['operator', 'contact:facebook', 'contact:phone', 'opening_hours', 
          'cuisine', 'network',  'website', 'contact:website', 'phone', 
          'branch', 'route_ref', 'addr:flats', 'brand', 'ref', 'addr:street', 
          'wikipedia', 'description', 'layer', 'level']

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
        print 'No such icon: ' + file_name
        return 'M 4,4 L 4,10 10,10 10,4 4,4', 0, 0
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
    shape, xx, yy = get_d_from_file(name)
    draw_point(shape, x, y, fill, size=16, xx=xx, yy=yy)

def draw_point(shape, x, y, fill, size=16, xx=0, yy=0):
    x = int(float(x))
    y = int(float(y))
    output_file.write('<path d="' + shape + \
            '" style="fill:#FFFFFF;opacity:0.5;stroke:#FFFFFF;stroke-width:3;stroke-linejoin:round;" transform="translate(' + \
         str(x - size / 2.0 - xx * 16) + ',' + str(y - size / 2.0 - yy * 16) + ')" />\n')
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
    return
    output_file.write('<text x="' + x + '" y="' + y + \
            '" style="font-size:10;text-anchor:middle;font-family:Myriad Pro;fill:#FFFFFF;stroke-linejoin:round;stroke-width:5;stroke:#FFFFFF;opacity:0.5;">' + text + '</text>')
    output_file.write('<text x="' + x + '" y="' + y + \
            '" style="font-size:10;text-anchor:middle;font-family:Myriad Pro;fill:#' + fill + ';">' + text + '</text>')

def point(k, v, x, y, fill, text_y):
    if ('node ' + k + ': ' + v) in missed_tags:
        missed_tags['node ' + k + ': ' + v] += 1
    else:
        missed_tags['node ' + k + ': ' + v] = 1
    #output_file.circle(float(x), float(y), 2, fill=fill, color=fill)
    text = k + ': ' + v
    if type(text) == unicode:
        text = text.encode('utf-8')
    output_file.write('<text x="' + str(x) + '" y="' + str(int(float(y)) + text_y + 10) + \
            '" style="font-size:10;text-anchor:middle;font-family:Myriad Pro;fill:#FF0000;">' + text + '</text>')

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
            for tag in way['tags']:
                if not (tag in ['landuse', 'layer']):
                    point(tag, str(way['tags'][tag]), c.x, c.y, '000000', text_y)
                    text_y += 10
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
            elif v == 'steps': style += '5;stroke-dasharray:1,2;stroke-linecap:round'
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
    return key in undraw or 'name' in key or 'addr' in key

def draw_nodes():
    print 'Draw nodes...'

    for node_id in node_map:
        node = node_map[node_id]
        flinged = flinger.fling(Geo(node['lat'], node['lon']))
        x = `flinged.x`
        y = `flinged.y`
        text_y = 0
        if 'tags' in node:
            pairs = node['tags']
        else:
            pairs = {}
        fill = '444444'
        if 'colour' in pairs:
            if pairs['colour'] == 'blue':
                fill='2233AA'
                radius=3

        if pairs == {}:
            pass
        elif 'amenity' in pairs:
            k = 'amenity'
            v = pairs['amenity']
            if v in ['bench', 'bicycle_parking', 'cafe', 'waste_basket', 'clinic',
                     'restaurant', 'pharmacy', 'drinking_water', 'toilets',
                     'theatre', 'bar', 'bank', 'pub', 'post_office']:
                draw_point_shape(v, x, y, fill)
            elif v == 'fast_food':
                main = 'fast_food'
                if 'operator' in pairs:
                    if pairs['operator'] == "McDonald's":
                        main = 'mcdonalds'
                if 'operator:en' in pairs:
                    if pairs['operator:en'] == "McDonald's":
                        main = 'mcdonalds'
                draw_point_shape(main, x, y, fill)
            elif v == 'shop':
                if 'shop' in pairs:
                    if pairs['shop'] in ['fishing']:
                        draw_point_shape('shop_' + pairs['shop'], x, y, fill)
            elif v == 'fountain':
                draw_point_shape('fountain', x, y, water_border_color)
            elif v == 'recycling':
                if not 'recycling_type' in pairs:
                    draw_point_shape('recycling', x, y, fill)
            else:
                point(k, v, flinged.x, flinged.y, fill, text_y)
                text_y += 10
            for k in pairs:
                if 'karaoke' in pairs:
                    if pairs['karaoke'] == 'yes':
                        draw_point_shape('microphone', flinged.x + 16, y, fill)
                    else:
                        point(k, pairs[k], x, y, fill, text_y)
                elif not no_draw(k) and k != 'amenity':
                    point(k, pairs[k], x, y, fill, text_y)
                    text_y += 10
        elif 'natural' in pairs:
            k = 'natural'
            v = pairs['natural']
            if v == 'tree':
                main = 'tree'
                if 'leaf_type' in pairs and pairs['leaf_type'] in ['broadleaved', 'needleleaved']:
                    main = pairs['leaf_type']
                if 'denotation' in pairs and pairs['denotation'] == 'urban':
                    draw_point_shape([main, 'urban_tree_pot'], x, y, wood_color)
                else:
                    draw_point_shape(main, x, y, wood_color)
            elif v == 'cave_entrance':
                draw_point_shape('cave', x, y, fill)
            elif v == 'bush':
                draw_point_shape('bush', x, y, wood_color)
            else:
                point(k, v, flinged.x, flinged.y, fill, text_y)
                text_y += 10
        elif 'entrance' in pairs:
            k = 'entrance'
            v = pairs['entrance']
            if v == 'yes':
                draw_point_shape('entrance', x, y, fill)
            elif v == 'staircase':
                draw_point_shape('staircase', x, y, fill)
        elif 'highway' in pairs:
            k = 'highway'
            v = pairs['highway']
            if v == 'crossing':
                shape = 'crossing'
                if 'crossing' in pairs:
                    if pairs['crossing'] == 'zebra':
                        shape = 'zebra'
                elif 'crossing_ref' in pairs:
                    if pairs['crossing_ref'] == 'zebra':
                        shape = 'zebra'
                draw_point_shape(shape, x, y, fill)
            elif v == 'street_lamp':
                draw_point_shape('street_lamp', x, y, fill)
        else:
            for k in pairs:
                if not no_draw(k):
                    point(k, pairs[k], x, y, fill, text_y)
                    text_y += 10
            

        for k in []:
            v = pairs[k]
            if k == 'amenity':
                if v in ['bench', 'bicycle_parking', 'cafe', 'waste_basket', 
                         'restaurant', 'pharmacy', 'drinking_water', 'toilets',
                         'fast_food', 'theatre']:
                    draw_point_shape(v, x, y, fill)
            elif k == 'artwork_type':
                if v == 'statue':
                    draw_point_shape('monument', x, y, fill)
                if v == 'sculpture':
                    draw_point_shape('monument', x, y, fill)
                else:
                    point(k, v, flinged.x, flinged.y, fill, text_y)
                    text_y += 10
            elif k == 'barrier':
                if v == 'lift_gate':
                    draw_point_shape('liftgate', x, y, fill)
            elif k in ['crossing', 'crossing_ref']:
                if v == 'zebra':
                    draw_point_shape('crossing', x, y, fill)
            elif k == 'entrance':
                draw_point_shape('entrance', x, y, fill)
            elif k == 'highway':
                if v == 'street_lamp': 
                    draw_point_shape('street_lamp', x, y, fill)
                elif v == 'bus_stop': 
                    draw_point_shape('bus_stop', x, y, fill)
                elif v == 'traffic_signals': 
                    draw_point_shape('traffic_signal', x, y, fill)
                elif v == 'crossing':    
                    if not ('crossing' in pairs):
                        draw_point_shape('crossing', x, y, fill)
                else:
                    point(k, v, flinged.x, flinged.y, fill, text_y)
                    text_y += 10
            elif k == 'man_made':
                if v == 'pole':
                    draw_point_shape('pole', x, y, fill)
                elif v == 'flagpole':
                    draw_point_shape('flagpole', x, y, fill)
                else:
                    point(k, v, flinged.x, flinged.y, fill, text_y)
                    text_y += 10
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
                    point(k, v, flinged.x, flinged.y, fill, text_y)
                    text_y += 10
            elif k == 'traffic_calming':
                if v == 'bump':
                    draw_point_shape('bump', x, y, fill)
                else:
                    point(k, v, flinged.x, flinged.y, fill, text_y)
                    text_y += 10
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
            elif k in undraw or ('name' in k):
                if k == 'route_ref':
                    v = v.replace(';', ' ')
                draw_text(v, x, str(flinged.y + 18 + text_y), fill)
                text_y += 10
            elif k in ['layer', 'level', 'source', 'note', 'description']:
                pass  # NOTHING TO DRAW
            else:
                point(k, v, flinged.x, flinged.y, fill, text_y)
                text_y += 10

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
    print tag + ' (' + str(missed_tags[tag]) + ')'

sys.exit(0)

top_authors = sorted(authors.keys(), key=lambda x: -authors[x])
for author in top_authors:
    print author + ': ' + str(authors[author])
