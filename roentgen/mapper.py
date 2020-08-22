#!/usr/bin/python
# -*- coding: utf-8 -*- from __future__ import unicode_literals

"""
Simple tool for working with OpenStreetMap data.

Author: Sergey Vartanov (me@enzet.ru).
"""

import copy
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
from datetime import datetime

sys.path.append('../lib')

import svg
from vector import Vector

background_color = 'EEEEEE'  # 'DDDDDD'
outline_color = 'FFFFFF'
beach_color = 'F0E0C0'
building_color = 'EEEEEE'  # 'D0D0C0'
building_border_color = 'DDDDDD'  # 'AAAAAA'
construction_color = 'CCCCCC'
cycle_color = '4444EE'
desert_color = 'F0E0D0'
foot_color = 'B89A74'
indoor_color = 'E8E4E0'
indoor_border_color = 'C0B8B0'
foot_border_color = 'FFFFFF'
grass_color = 'CFE0A8'
grass_border_color = 'BFD098'
guide_strips_color = '228833'
parking_color = 'DDCC99'
platform_color = 'CCCCCC'
platform_border_color = 'AAAAAA'
playground_color = '884400'
primary_border_color = '888888'  # 'AA8800'
primary_color = 'FFFFFF'  # 'FFDD66'
private_access_color = '884444'
road_border_color = 'CCCCCC'
sand_color = 'F0E0D0'
water_color = 'AACCFF'
water_border_color = '6688BB'
wood_color = 'B8CC84'
wood_border_color = 'A8BC74'

icons_file_name = '../icons/icons.svg'
tags_file_name = '../data/tags.yml'
colors_file_name = '../data/colors.yml'
missed_tags_file_name = '../missed_tags.yml'

tags_to_write = set(['operator', 'opening_hours', 'cuisine', 'network',  
                 'website', 'website_2', 'STIF:zone', 'opening_hours:url',
                 'phone', 'branch', 'route_ref', 'brand', 'ref', 'wikipedia', 
                 'description', 'wikidata', 'name', 'alt_name', 
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

tags_to_skip = set(['note', 'layer', 'level', 'source', 'building:part', 
        'comment', 'FIXME', 'source_ref', 'naptan:verified:note', 'fixme',
        'building:levels', 'ref:opendataparis:adresse', 'indoor', 'level:ref',
        'ref:opendataparis:geo_point_2d', 'created_by', 'mapillary'])

prefix_to_skip = set(['source', 'mapillary'])

def get_d_from_file(file_name):
    path, x, y = icons.get_path(file_name)
    if path:
        return path, x, y
    else:
        # print('No such icon: ' + file_name)
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


def get_path(nodes, shift=Vector()):
    path = ''
    prev_node = None
    for node_id in nodes:
        node = node_map[node_id]
        flinged1 = flinger.fling(Geo(node['lat'], node['lon'])) + shift
        if prev_node:
            flinged2 = flinger.fling(Geo(prev_node['lat'], prev_node['lon'])) + shift
            path += ('L ' + `flinged1.x` + ',' + `flinged1.y` + ' ')
        else:
            path += ('M ' + `flinged1.x` + ',' + `flinged1.y` + ' ')
        prev_node = node_map[node_id]
    if nodes[0] == nodes[-1]:
        path += 'Z'
    return path


def draw_point_shape(name, x, y, fill, tags=None):
    if not isinstance(name, list):
        name = [name]
    for one_name in name:
        shape, xx, yy = get_d_from_file(one_name)
        draw_point_outline(shape, x, y, fill, size=16, xx=xx, yy=yy)
    for one_name in name:
        shape, xx, yy = get_d_from_file(one_name)
        draw_point(shape, x, y, fill, size=16, xx=xx, yy=yy, tags=tags)

def draw_point_outline(shape, x, y, fill, size=16, xx=0, yy=0):
    x = int(float(x))
    y = int(float(y))
    opacity = 0.5
    outline_fill = outline_color
    if not options.mode in ['user-coloring', 'time']:
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

def draw_point(shape, x, y, fill, size=16, xx=0, yy=0, tags=None):
    x = int(float(x))
    y = int(float(y))
    output_file.write('<path d="' + shape + \
         '" style="fill:#' + fill + ';fill-opacity:1" transform="translate(' + \
         str(x - size / 2.0 - xx * 16) + ',' + str(y - size / 2.0 - yy * 16) + ')">')
    if tags:
        output_file.write('<title>')
        output_file.write('\n'.join(map (lambda x: x + ': ' + tags[x], tags)))
        output_file.write('</title>')
    output_file.write('</path>\n')

def draw_text(text, x, y, fill, size=10, out_fill='FFFFFF', out_opacity=0.5, 
        out_fill_2=None, out_opacity_2=1.0):
    """
    Drawing text.

      ######     ###  outline 2
     #------#    ---  outline 1
    #| Text |#
     #------# 
      ######  
    """
    if type(text) == unicode:
        text = text.encode('utf-8')
    text = text.replace('&', 'and')
    if out_fill_2:
        output_file.write('<text x="' + str(x) + '" y="' + str(y) + \
                '" style="font-size:' + str(size) + ';text-anchor:middle;font-family:Myriad Pro;fill:#' + out_fill_2 + ';stroke-linejoin:round;stroke-width:5;stroke:#' + out_fill_2 + ';opacity:' + str(out_opacity_2) + ';">' + text + '</text>')
    if out_fill:
        output_file.write('<text x="' + str(x) + '" y="' + str(y) + \
                '" style="font-size:' + str(size) + ';text-anchor:middle;font-family:Myriad Pro;fill:#' + out_fill + ';stroke-linejoin:round;stroke-width:5;stroke:#' + out_fill + ';opacity:' + str(out_opacity) + ';">' + text + '</text>')
    output_file.write('<text x="' + str(x) + '" y="' + str(y) + \
            '" style="font-size:' + str(size) + ';text-anchor:middle;font-family:Myriad Pro;fill:#' + fill + ';">' + text + '</text>')

def point(k, v, x, y, fill, text_y):
    text = k + ': ' + v
    if type(text) == unicode:
        text = text.encode('utf-8')
    draw_text(text, x, float(y) + text_y + 18, '734A08')

def construct_text(tags, processed):
    for key in tags:
        tags[key] = tags[key].replace('&quot;', '"')
    texts = []
    addr = None
    name = None
    alt_name = None
    if 'name' in tags:
        name = tags['name']
        tags.pop('name', None)
    if 'name:ru' in tags:
        if not name:
            name = tags['name:ru']
            tags.pop('name:ru', None)
        tags.pop('name:ru', None)
    if 'name:en' in tags:
        if not name:
            name = tags['name:en']
            tags.pop('name:en', None)
        tags.pop('name:en', None)
    if 'alt_name' in tags:
        if alt_name:
            alt_name += ', '
        else:
            alt_name = ''
        alt_name += tags['alt_name']
        tags.pop('alt_name')
    if 'old_name' in tags:
        if alt_name:
            alt_name += ', '
        else:
            alt_name = ''
        alt_name += 'бывш. ' + tags['old_name']
    if 'addr:postcode' in tags:
        if addr:
            addr += ', '
        else:
            addr = ''
        addr += tags['addr:postcode']
        tags.pop('addr:postcode', None)
    if 'addr:country' in tags:
        if tags['addr:country'] == 'RU':
            addr = 'Россия'
        else:
            addr = tags['addr:country']
        tags.pop('addr:country', None)
    if 'addr:city' in tags:
        if addr:
            addr += ', '
        else:
            addr = ''
        addr += tags['addr:city']
        tags.pop('addr:city', None)
    if 'addr:street' in tags:
        if addr:
            addr += ', '
        else:
            addr = ''
        street = tags['addr:street']
        if street.startswith('улица '):
            street = 'ул. ' + street[len('улица '):]
        addr += street
        tags.pop('addr:street', None)
    if 'addr:housenumber' in tags:
        if addr:
            addr += ', '
        else:
            addr = ''
        addr += tags['addr:housenumber']
        tags.pop('addr:housenumber', None)
    if name:
        texts.append({'text': name, 'fill': '000000'})
    if alt_name:
        texts.append({'text': '(' + alt_name + ')'})
    if addr:
        texts.append({'text': addr})
    if options.draw_captions == 'main':
        return texts
    if 'route_ref' in tags:
        texts.append({'text': tags['route_ref'].replace(';', ' ')})
        tags.pop('route_ref', None)
    if 'cladr:code' in tags:
        texts.append({'text': tags['cladr:code'], 'size': 7})
        tags.pop('cladr:code', None)
    if 'website' in tags:
        link = tags['website']
        if link[:7] == 'http://':
            link = link[7:]
        if link[:8] == 'https://':
            link = link[8:]
        if link[:4] == 'www.':
            link = link[4:]
        if link[-1] == '/':
            link = link[:-1]
        link = link[:25] + ('...' if len(tags['website']) > 25 else '')
        texts.append({'text': link, 'fill': '000088'})
        tags.pop('website', None)
    for k in ['phone']:
        if k in tags:
            texts.append({'text': tags[k], 'fill': '444444'})
            tags.pop(k)
    for tag in tags:
        if to_write(tag) and not (tag in processed):
            #texts.append({'text': tag + ': ' + tags[tag]})
            texts.append({'text': tags[tag]})
    return texts


def wr(text, x, y, fill, text_y, size=10):
    if type(text) == str:
        text = text.decode('utf-8')
    text = text[:26] + ('...' if len(text) > 26 else '')
    text = text.encode('utf-8')
    draw_text(text, x, float(y) + text_y + 8, fill, size=size)

# Ways drawing

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


def get_float(string):
    try:
        return float(string)
    except ValueError:
        return 0


def get_user_color(user):
    if user == '': 
        return '000000'
    rgb = hex(abs(hash(options.seed + user)))[-6:]
    r = int(rgb[0:2], 16)
    g = int(rgb[2:4], 16)
    b = int(rgb[4:6], 16)
    c = (r + g + b) / 3.
    cc = 0
    r = r * (1 - cc) + c * cc
    g = g * (1 - cc) + c * cc
    b = b * (1 - cc) + c * cc
    h = hex(int(r))[2:] + hex(int(g))[2:] + hex(int(b))[2:]
    return '0' * (6 - len(h)) + h


def get_time_color(time):
    if not time:
        return '000000'
    time = datetime.strptime(time, '%Y-%m-%dT%H:%M:%SZ')
    delta = (datetime.now() - time).total_seconds()
    time_color = hex(0xFF - min(0xFF, int(delta / 500000.)))[2:]
    i_time_color = hex(min(0xFF, int(delta / 500000.)))[2:]
    if len(time_color) == 1:
        time_color = '0' + time_color
    if len(i_time_color) == 1:
        i_time_color = '0' + i_time_color
    return time_color + 'AA' + i_time_color


def construct_ways(drawing):
    for way_id in way_map:
        way = way_map[way_id]
        tags = way['tags']
        if not (options.level is None):
            if 'level' in tags:
                levels = map(lambda x:float(x), tags['level'].split(';'))
                if not options.level in levels:
                    continue
            else:
                continue
        user = way['user'] if 'user' in way else ''
        time = way['timestamp'] if 'timestamp' in way else None
        construct_way(drawing, way['nodes'], tags, None, user, time)


def construct_way(drawing, nodes, tags, path, user, time):
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
    layer = 0
    level = 0

    if 'layer' in tags:
        layer = get_float(tags['layer'])
    if 'level' in tags:
        levels = map(lambda x:float(x), tags['level'].split(';'))
        level = sum(levels) / len(levels)

    layer = 100 * level + 0.01 * layer

    if nodes:
        c = line_center(nodes)

    if options.mode == 'user-coloring':
        user_color = get_user_color(user)
        drawing['ways'].append({'kind': 'way', 'nodes': nodes, 'path': path,
            'style': 'fill:none;stroke:#' + user_color + ';stroke-width:1;'})
        return

    if options.mode == 'time':
        if not time:
            return
        time_color = get_time_color(time)
        drawing['ways'].append({'kind': 'way', 'nodes': nodes, 'path': path,
            'style': 'fill:none;stroke:#' + time_color + ';stroke-width:1;'})
        return

    # Indoor features

    if 'indoor' in tags:
        v = tags['indoor']
        style = 'stroke:' + indoor_border_color + ';stroke-width:1;'
        if v == 'area':
            style += 'fill:#' + indoor_color + ';'
            layer += 10
        elif v == 'corridor':
            style += 'fill:#' + indoor_color + ';'
            layer += 11
        elif v in ['yes', 'room', 'elevator']:
            style += 'fill:#' + indoor_color + ';'
            layer += 12
        elif v == 'column':
            style += 'fill:#' + indoor_border_color + ';'
            layer += 13
        drawing['ways'].append({'kind': 'way', 'nodes': nodes, 'layer': layer,
            'priority': 50, 'style': style, 'path': path})

    # Natural

    if 'natural' in tags:
        v = tags['natural']
        style = 'stroke:none;'
        if v == 'wood':
            style += 'fill:#' + wood_color + ';'
            layer += 21
        elif v == 'scrub':
            style += 'fill:#' + wood_color + ';'
            layer += 21
        elif v == 'sand':
            style += 'fill:#' + sand_color + ';'
            layer += 20
        elif v == 'beach':
            style += 'fill:#' + beach_color + ';'
            layer += 20
        elif v == 'desert':
            style += 'fill:#' + desert_color + ';'
            layer += 20
        elif v == 'forest':
            style += 'fill:#' + wood_color + ';'
            layer += 21
        elif v == 'tree_row':
            style += 'fill:none;stroke:#' + wood_color + ';stroke-width:5;'
            layer += 21
        elif v == 'water':
            style = 'fill:#' + water_color + ';stroke:#' + \
                water_border_color + ';stroke-width:1.0;'
            layer += 21
        drawing['ways'].append({'kind': 'way', 'nodes': nodes, 'layer': layer,
            'priority': 50, 'style': style, 'path': path})

    # Landuse

    if 'landuse' in tags:
        style = 'fill:none;stroke:none;'
        if tags['landuse'] == 'grass':
            style = 'fill:#' + grass_color + ';stroke:#' + grass_border_color + ';'
            layer += 20
        elif tags['landuse'] == 'conservation':
            style = 'fill:#' + grass_color + ';stroke:none;'
            layer += 20
        elif tags['landuse'] == 'forest':
            style = 'fill:#' + wood_color + ';stroke:none;'
            layer += 20
        elif tags['landuse'] == 'garages':
            style = 'fill:#' + parking_color + ';stroke:none;'
            layer += 21
            shapes, fill, processed = \
                process.get_icon(tags, scheme, '444444')
            if nodes:
                drawing['nodes'].append({'shapes': shapes, 'tags': tags,
                    'x': c.x, 'y': c.y, 'color': fill, 'path': path,
                    'processed': processed})
        elif tags['landuse'] == 'construction':
            layer += 20
            style = 'fill:#' + construction_color + ';stroke:none;'
        elif tags['landuse'] in ['residential', 'commercial']:
            return
        drawing['ways'].append({'kind': 'way', 'nodes': nodes, 'layer': layer,
            'priority': 50, 'style': style, 'path': path})
    
    # Building

    if 'building' in tags:
        style = 'fill:none;stroke:none;'
        text_y = 0
        layer += 40
        levels = 1
        if 'building:levels' in tags:
            levels = float(tags['building:levels'])
        style = 'fill:#' + building_color + ';stroke:#' + \
            building_border_color + ';opacity:1.0;'
        shapes, fill, processed = process.get_icon(tags, scheme, '444444')
        if 'height' in tags:
            layer += float(tags['height'])
        if nodes:
            drawing['nodes'].append({'shapes': shapes, 'x': c.x, 'y': c.y, 
                'color': fill, 'priority': 1, 'processed': processed, 
                'tags': tags, 'path': path})
        drawing['ways'].append({'kind': 'building', 'nodes': nodes, 
            'layer': layer, 'priority': 50, 'style': style, 'path': path, 
            'levels': levels})

    # Amenity

    if 'amenity' in tags:
        style = 'fill:none;stroke:none;'
        layer += 21
        if tags['amenity'] == 'parking':
            style = 'fill:#' + parking_color + ';stroke:none;opacity:0.5;'
            shapes, fill, processed = process.get_icon(tags, scheme, '444444')
            if nodes:
                drawing['nodes'].append({'shapes': shapes, 'x': c.x, 'y': c.y, 
                    'color': fill, 'priority': 1, 'processed': processed, 
                    'tags': tags, 'path': path})
        drawing['ways'].append({'kind': 'way', 'nodes': nodes, 'layer': layer,
            'priority': 50, 'style': style, 'path': path})

    # Waterway

    if 'waterway' in tags:
        style = 'fill:none;stroke:none;'
        layer += 21
        if tags['waterway'] == 'riverbank':
            style = 'fill:#' + water_color + ';stroke:#' + \
                water_border_color + ';stroke-width:1.0;'
        elif tags['waterway'] == 'river':
            style = 'fill:none;stroke:#' + water_color + ';stroke-width:10.0;'
        drawing['ways'].append({'kind': 'way', 'nodes': nodes, 'layer': layer,
            'priority': 50, 'style': style, 'path': path})

    # Railway

    if 'railway' in tags:
        style = 'fill:none;stroke:none;'
        layer += 41
        v = tags['railway']
        style = 'fill:none;stroke-dasharray:none;stroke-linejoin:round;' + \
            'stroke-linecap:round;stroke-width:'
        if v == 'subway': style += '10;stroke:#DDDDDD;'
        if v in ['narrow_gauge', 'tram']: 
            style += '2;stroke:#000000;'
        if v == 'platform': 
            style = 'fill:#' + platform_color + ';stroke:#' + \
                platform_border_color + 'stroke-width:1;'
        else:
            return
        drawing['ways'].append({'kind': 'way', 'nodes': nodes, 'layer': layer,
            'priority': 50, 'style': style, 'path': path})

    # Highway

    if 'highway' in tags:
        style = 'fill:none;stroke:none;'
        layer += 42
        v = tags['highway']
        if False: #'tunnel' in tags and tags['tunnel'] == 'yes':
            style = 'fill:none;stroke:#FFFFFF;stroke-dasharray:none;' + \
                'stroke-linejoin:round;stroke-linecap:round;stroke-width:10;'
            drawing['ways'].append({'kind': 'way', 'nodes': nodes, 
                'layer': layer, 'priority': 50, 'style': style,
                'path': path})

        style = 'fill:none;stroke:#' + road_border_color + \
            ';stroke-dasharray:none;' + \
            'stroke-linejoin:round;stroke-linecap:round;stroke-width:'

        # Highway outline

        if v == 'motorway': style += '33'
        elif v == 'trunk': style += '31'
        elif v == 'primary': style += '29;stroke:#' + primary_border_color
        elif v == 'secondary': style += '27'
        elif v == 'tertiary': style += '25'
        elif v == 'unclassified': style += '17'
        elif v == 'residential': style += '17'
        elif v == 'service': 
            if 'service' in tags and tags['service'] == 'parking_aisle': 
                style += '7'
            else:
                style += '11'
        elif v == 'track': style += '3'
        elif v in ['footway', 'pedestrian', 'cycleway']: 
            if not ('area' in tags and tags['area'] == 'yes'):
                style += '3;stroke:#' + foot_border_color
        elif v in ['steps']: style += '6;stroke:#' + foot_border_color + ';stroke-linecap:butt;'
        else: style = None
        if style:
            style += ';'
            drawing['ways'].append({'kind': 'way', 'nodes': nodes, 
                'layer': layer + 41, 'priority': 50, 'style': style,
                'path': path})

        # Highway main shape

        style = 'fill:none;stroke:#FFFFFF;stroke-linecap:round;' + \
            'stroke-linejoin:round;stroke-width:'

        priority = 50

        if v == 'motorway': style += '31'
        elif v == 'trunk': style += '29'
        elif v == 'primary': style += '27;stroke:#' + primary_color
        elif v == 'secondary': style += '25'
        elif v == 'tertiary': style += '23'
        elif v == 'unclassified': style += '15'
        elif v == 'residential': style += '15'
        elif v == 'service': 
            if 'service' in tags and tags['service'] == 'parking_aisle': 
                style += '5'
            else:
                style += '9'
        elif v == 'cycleway': 
            style += '1;stroke-dasharray:8,2;istroke-linecap:butt;' + \
                'stroke:#' + cycle_color
        elif v in ['footway', 'pedestrian']:
            priority = 55
            if 'area' in tags and tags['area'] == 'yes':
                style += '1;stroke:none;fill:#DDDDDD'
                layer -= 55  # FIXME!
            else:
                style += '1.5;stroke-dasharray:7,3;stroke-linecap:round;' + \
                    'stroke:#'
                if 'guide_strips' in tags and tags['guide_strips'] == 'yes':
                    style += guide_strips_color
                else:
                    style += foot_color
        elif v == 'steps': 
            style += '5;stroke-dasharray:1.5,2;stroke-linecap:butt;' + \
                'stroke:#' 
            if 'conveying' in tags:
                style += '888888'
            else:
                style += foot_color
        elif v == 'path': 
            style += '1;stroke-dasharray:5,5;stroke-linecap:butt;' + \
                'stroke:#' + foot_color
        style += ';'
        drawing['ways'].append({'kind': 'way', 'nodes': nodes, 'layer': layer + 42,
            'priority': priority, 'style': style, 'path': path})
        if 'oneway' in tags and tags['oneway'] == 'yes' or \
            'conveying' in tags and tags['conveying'] == 'forward':
            for k in range(7):
                drawing['ways'].append({'kind': 'way', 'nodes': nodes, 'layer': layer + 43, 'priority': 50, 'path': path, 'style': 'fill:none;stroke:#222288;stroke-linecap:butt;stroke-width:' + str(7 - k) + ';stroke-dasharray:' + str(k) + ',' + str(40 - k) + ';'})
        if 'access' in tags and tags['access'] == 'private':
            drawing['ways'].append({'kind': 'way', 'nodes': nodes, 
                'layer': layer + 0.1, 'priority': 50, 'path': path,
                'style': 'fill:none;' + \
                        'stroke:#' + private_access_color + ';' + \
                        'stroke-linecap:butt;' + \
                        'stroke-width:10;stroke-dasharray:1,5;' + \
                        'opacity:0.4;'})
    # Leisure

    if 'leisure' in tags:
        style = 'fill:none;stroke:none;'
        layer += 21
        if tags['leisure'] == 'playground':
            style = 'fill:#' + playground_color + ';opacity:0.2;'
            if nodes:
                draw_point_shape('toy_horse', c.x, c.y, '444444')
        elif tags['leisure'] == 'garden':
            style = 'fill:#' + grass_color + ';'
        elif tags['leisure'] == 'pitch':
            style = 'fill:#' + playground_color + ';opacity:0.2;'
        elif tags['leisure'] == 'park':
            return 
        else:
            style = 'fill:#FF0000;opacity:0.2;'
        drawing['ways'].append({'kind': 'way', 'nodes': nodes, 'layer': layer,
            'priority': 50, 'style': style, 'path': path})

    # Barrier

    if 'barrier' in tags:
        style = 'fill:none;stroke:none;'
        layer += 40
        if tags['barrier'] == 'hedge':
            style += 'fill:none;stroke:#' + wood_color + ';stroke-width:4;'
        elif tags['barrier'] == 'fense':
            style += 'fill:none;stroke:#000000;stroke-width:1;opacity:0.4;'
        elif tags['barrier'] == 'kerb':
            style += 'fill:none;stroke:#000000;stroke-width:1;opacity:0.2;'
        else:
            style += 'fill:none;stroke:#000000;stroke-width:1;opacity:0.3;'
        drawing['ways'].append({'kind': 'way', 'nodes': nodes, 'layer': layer,
            'priority': 50, 'style': style, 'path': path})

    # Border

    if 'border' in tags:
        style = 'fill:none;stroke:none;'
        style += 'fill:none;stroke:#FF0000;stroke-width:0.5;' + \
            'stroke-dahsarray:10,20;'
        drawing['ways'].append({'kind': 'way', 'nodes': nodes, 'layer': layer,
            'priority': 50, 'style': style, 'path': path})
    if 'area:highway' in tags:
        style = 'fill:none;stroke:none;'
        if tags['area:highway'] == 'yes':
            style += 'fill:#FFFFFF;stroke:#DDDDDD;stroke-width:1;'
        drawing['ways'].append({'kind': 'way', 'nodes': nodes, 'layer': layer,
            'priority': 50, 'style': style, 'path': path})
    #drawing['ways'].append({'kind': 'way', 'nodes': nodes, 'layer': layer,
    #    'priority': 50, 'style': style, 'path': path})
    if False:
        if 'highway' in tags and tags['highway'] != 'steps' and not ('surface' in tags):
            drawing['ways'].append({'kind': 'way', 'nodes': nodes, 
                'layer': layer + 0.1, 'priority': 50, 'path': path,
                'style': 'fill:none;' + \
                'stroke:#FF0000;stroke-linecap:butt;' + \
                'stroke-width:5;opacity:0.4;'})
            #draw_text('no surface', cx, cy, 'FF0000', out_opacity='1.0', 
            #    out_fill_2='FF0000', out_opacity_2=1.0)


def glue_ways(ways):
    new_ways = []
    processed = []
    for way in ways:
        if way['id'] in processed:
            continue
        if way['nodes'][0] == way['nodes'][-1]:
            new_ways.append(way['nodes'])
            processed.append(way['id'])
        for other_way in ways:
            if way == other_way:
                continue
            if way['id'] in processed or other_way['id'] in processed:
                break
            if way['nodes'][0] == other_way['nodes'][0]:
                o = other_way['nodes'][1:]
                o.reverse()
                way['nodes'] = o + way['nodes']
                processed.append(other_way['id'])
            elif way['nodes'][0] == other_way['nodes'][-1]:
                way['nodes'] = other_way['nodes'][:-1] + way['nodes']
                processed.append(other_way['id'])
            elif way['nodes'][-1] == other_way['nodes'][-1]:
                o = other_way['nodes'][:-1]
                o.reverse()
                way['nodes'] += o
                processed.append(other_way['id'])
            elif way['nodes'][-1] == other_way['nodes'][0]:
                way['nodes'] += other_way['nodes'][1:]
                processed.append(other_way['id'])
            if way['nodes'][0] == way['nodes'][-1]:
                new_ways.append(way['nodes'])
                processed.append(way['id'])
    for way in ways:
        if not (way['id'] in processed):
            new_ways.append(way['nodes'])

    return new_ways


def construct_relations(drawing):
    for relation_id in relation_map:
        relation = relation_map[relation_id]
        tags = relation['tags']
        if not (options.level is None):
            if 'level' in tags:
                levels = map(lambda x:float(x), tags['level'].split(';'))
                if not options.level in levels:
                    continue
            else:
                continue
        if 'type' in tags and tags['type'] == 'multipolygon':
            style = 'fill:#FFEEEE;stroke:#FF0000;stroke-width:0.5;'
            inners, outers = [], []
            for member in relation['members']:
                if member['type'] == 'way':
                    if member['role'] == 'inner':
                        if member['ref'] in way_map:
                            inners.append(way_map[member['ref']])
                    elif member['role'] == 'outer':
                        if member['ref'] in way_map:
                            outers.append(way_map[member['ref']])
            p = ''
            inners_path = glue_ways(inners)
            outers_path = glue_ways(outers)
            for way in outers_path:
                path = get_path(way)
                p += path + ' '
            for way in inners_path:
                way.reverse()
                path = get_path(way)
                p += path + ' '
            construct_way(drawing, None, tags, p, '', None)


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
    if key in tags_to_skip:
        return False
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
                draw_point_shape(shape, x + xxx, y, fill, tags=tags)
                points.append(Vector(x + xxx, y))
                xxx += 16
    else:
        for shape in shapes:
            draw_point_shape(shape, x + xxx, y, fill, tags=tags)
            xxx += 16

    if options.draw_captions != 'no':
        write_tags = construct_text(tags, processed)

        for text_struct in write_tags:
            fill = text_struct['fill'] if 'fill' in text_struct else '444444'
            size = text_struct['size'] if 'size' in text_struct else 10
            text_y += size + 1
            wr(text_struct['text'], x, y, fill, text_y, size=size)

        if show_missed_tags:
            for k in tags:
                if not no_draw(k) and not k in processed:
                    point(k, tags[k], x, y, fill, text_y)
                    text_y += 10

def construct_nodes(drawing):
    """
    Draw nodes.
    """
    print('Draw nodes...')

    start_time = datetime.now()

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

        if not (options.level is None):
            if 'level' in tags:
                levels = map(lambda x:float(x), tags['level'].replace(',', '.').split(';'))
                if not options.level in levels:
                    continue
            else:
                continue

        shapes, fill, processed = process.get_icon(tags, scheme)

        if options.mode == 'user-coloring':
            fill = get_user_color(node['user'])
        if options.mode == 'time':
            fill = get_time_color(node['timestamp'])

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

        if shapes == [] and tags != {}:
            shapes = [['circle']]

        drawing['nodes'].append({'shapes': shapes, 
            'x': x, 'y': y, 'color': fill, 'processed': processed, 
            'tags': tags})

    ui.write_line(-1, len(node_map))
    print('Nodes drawed in ' + str(datetime.now() - start_time) + '.')
    print('Tags processed: ' + str(processed_tags) + ', tags skipped: ' +
        str(skipped_tags) + ' (' +
        str(processed_tags / float(processed_tags + skipped_tags) * 100) + ' %).')

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
        if way['kind'] == 'way':
            if way['nodes']:
                path = get_path(way['nodes'])
                output_file.write('<path d="' + path + '" ' + \
                    'style="' + way['style'] + '" />\n')
            else:
                output_file.write('<path d="' + way['path'] + '" ' + \
                    'style="' + way['style'] + '" />\n')
    output_file.write('<g style="opacity:0.1;">\n')
    for way in ways:
        if way['kind'] == 'building':
            if way['nodes']:
                shift = Vector(-5, 5)
                if 'levels' in way:
                    shift = Vector(-5 * way['levels'], 5 * way['levels'])
                for i in range(len(way['nodes']) - 1):
                    node_1 = node_map[way['nodes'][i]]
                    node_2 = node_map[way['nodes'][i + 1]]
                    flinged_1 = flinger.fling(Geo(node_1['lat'], node_1['lon']))
                    flinged_2 = flinger.fling(Geo(node_2['lat'], node_2['lon']))
                    output_file.write('<path d="M ' + `flinged_1.x` + ',' + `flinged_1.y` + ' L ' + `flinged_2.x` + ',' + `flinged_2.y` + ' ' + `(flinged_2 + shift).x` + ',' + `(flinged_2 + shift).y` + ' ' + `(flinged_1 + shift).x` + ',' + `(flinged_1 + shift).y` + ' Z" style="fill:#000000;stroke:#000000;stroke-width:1;" />\n')
    output_file.write('</g>\n')
    for way in ways:
        if way['kind'] == 'building':
            if way['nodes']:
                shift = Vector(0, -0.5)
                if 'levels' in way:
                    shift = Vector(0 * way['levels'], -0.5 * way['levels'])
                for i in range(len(way['nodes']) - 1):
                    node_1 = node_map[way['nodes'][i]]
                    node_2 = node_map[way['nodes'][i + 1]]
                    flinged_1 = flinger.fling(Geo(node_1['lat'], node_1['lon']))
                    flinged_2 = flinger.fling(Geo(node_2['lat'], node_2['lon']))
                    output_file.write('<path d="M ' + `flinged_1.x` + ',' + `flinged_1.y` + ' L ' + `flinged_2.x` + ',' + `flinged_2.y` + ' ' + `(flinged_2 + shift).x` + ',' + `(flinged_2 + shift).y` + ' ' + `(flinged_1 + shift).x` + ',' + `(flinged_1 + shift).y` + ' Z" style="fill:#DDDDDD;stroke:#DDDDDD;stroke-width:1;opacity:1;" />\n')
    for way in ways:
        if way['kind'] == 'building':
            if way['nodes']:
                shift = Vector(0, -0.5)
                if 'levels' in way:
                    shift = Vector(0 * way['levels'], -0.5 * way['levels'])
                # shift = Vector()
                path = get_path(way['nodes'], shift=shift)
                output_file.write('<path d="' + path + '" ' + \
                    'style="' + way['style'] + ';opacity:1;" />\n')
    nodes = sorted(drawing['nodes'], key=node_sorter)
    for node in nodes:
        draw_shapes(node['shapes'], overlap, points, node['x'], node['y'], 
            node['color'], show_missed_tags, node['tags'], node['processed'])

# Actions

options = ui.parse_options(sys.argv)

if not options:
    sys.exit(1)

if options.mode in ['user-coloring', 'time']:
    background_color = '111111'
    outline_color = '111111'

input_file_name = options.input_file_name

if not os.path.isfile(input_file_name):
    print('Fatal: no such file: ' + input_file_name + '.')
    sys.exit(1)

full = False  # Full keys getting

if options.mode in ['user-coloring', 'time']:
    full = True

node_map, way_map, relation_map = osm_reader.parse_osm_file(input_file_name, 
    parse_ways=options.draw_ways, parse_relations=options.draw_ways, full=full)

output_file = svg.SVG(open(options.output_file_name, 'w+'))

w, h = 2650, 2650

if 'size' in options:
    w = options.size[0]
    h = options.size[1]

output_file.begin(w, h)
output_file.write('<title>Rӧntgen</title><style> path:hover {stroke: #FF0000;} </style>\n')
output_file.rect(0, 0, w, h, color=background_color)

minimum = Geo(180, 180)
maximum = Geo(-180, -180)

if 'boundary_box' in options:
    bb = options.boundary_box
    min1 = Geo(bb[1], bb[0])
    max1 = Geo(bb[3], bb[2])

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
    print('Compute borders...')
    minimum, maximum = get_min_max(node_map)
    flinger = GeoFlinger(minimum, maximum, Vector(25, 25), Vector(975, 975))
    print('Done.')

icons = extract_icon.IconExtractor(icons_file_name)

drawing = {'nodes': [], 'ways': []}

if options.draw_ways:
    construct_ways(drawing)
    construct_relations(drawing)

construct_nodes(drawing)

draw(drawing, show_missed_tags=options.show_missed_tags, 
     overlap=options.overlap, draw=options.draw_nodes)

if flinger.space.x == 0:
    output_file.rect(0, 0, w, flinger.space.y, color='FFFFFF')
    output_file.rect(0, h - flinger.space.y, w, flinger.space.y, color='FFFFFF')

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

    for node_id in node_map:
        node = node_map[node_id]
        i = int((node['lat'] - min1.lat) / lat_step)
        j = int((node['lon'] - min1.lon) / lon_step)
        if (0 <= i < lat_number) and (0 <= j < lon_number):
            matrix[i][j] += 1
            if 'tags' in node:
                matrix[i][j] += len(node['tags'])

    for way_id in way_map:
        way = way_map[way_id]
        if 'tags' in way:
            for node_id in way['nodes']:
                node = node_map[node_id]
                i = int((node['lat'] - min1.lat) / lat_step)
                j = int((node['lon'] - min1.lon) / lon_step)
                if (0 <= i < lat_number) and (0 <= j < lon_number):
                    matrix[i][j] += len(way['tags']) / float(len(way['nodes']))

    for i in range(lat_number):
        for j in range(lon_number):
            b = int(matrix[i][j] / 1)
            a = '%2x' % min(255, b)
            color = a + a + a
            color = color.replace(' ', '0')
            t1 = flinger.fling(Geo(min1.lat + i * lat_step, 
                min1.lon + j * lon_step))
            t2 = flinger.fling(Geo(min1.lat + (i + 1) * lat_step, 
                min1.lon + (j + 1) * lon_step))
            #output_file.write('<path d = "M ' + str(t1.x) + ',' + str(t1.y) + ' L ' + str(t1.x) + ',' + str(t2.y) + ' ' + str(t2.x) + ',' + str(t2.y) + ' ' + str(t2.x) + ',' + str(t1.y)  + '" style = "fill:#' + color + ';opacity:0.5;" />\n')
            output_file.text(((t1 + t2) * 0.5).x, ((t1 + t2) * 0.5).y + 40, \
                str(int(matrix[i][j])), size=80, color='440000', opacity=0.1, 
                    align='center')

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
    print(author + ': ' + str(authors[author]))

