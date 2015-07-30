"""
Reading OpenStreetMap data from XML file.

Author: Sergey Vartanov
"""

import datetime
import ui
import sys


def parse_node_full(node_data, silent=False):
    """
    Parse full node parameters using regular expressions: id, visible, version, 
    etc. For faster parsing use parse_node().
    """
    m = re.match('id="(.*)" visible="(.*)" version="(.*)" changeset="(.*)" ' + \
                 'timestamp="(.*)" user="(.*)" uid="(.*)" ' + \
                 'lat="(.*)" lon="(.*)"', node_data)
    if m:
        return {'id': int(m.group(1)), 'visible': m.group(2), 
                'changeset': m.group(3), 'timestamp': m.group(4), 
                'user': m.group(5), 'uid': m.group(6), 
                'lat': float(m.group(7)), 'lon': float(m.group(8))}
    else:
        if not silent:
            print 'Error: cannot parse node data: ' + node_data + '.'
        return None

def parse_node(text):
    """
    Just parse node identifier, latitude, and longitude.
    """
    id = text[4:text.find('"', 6)]
    lat_index = text.find('lat')
    lon_index = text.find('lon')
    lat = text[lat_index + 5:text.find('"', lat_index + 7)]
    lon = text[lon_index + 5:text.find('"', lon_index + 7)]
    return {'id': int(id), 'lat': float(lat), 'lon': float(lon)}

def parse_way_full(way_data, silent=False):
    """
    Parse full way parameters using regular expressions: id, visible, version,
    etc. For faster parsing use parse_way().
    """
    m = re.match('id="(.*)" visible="(.*)" version="(.*)" changeset="(.*)" ' + \
                 'timestamp="(.*)" user="(.*)" uid="(.*)"', way_data)
    if m:
        return {'id': m.group(1), 'visible': m.group(2), 
                'changeset': m.group(3), 'timestamp': m.group(4), 
                'user': m.group(5), 'uid': m.group(6)}
    else:
        if not silent:
            print 'Error: cannot parse way data: ' + way_data + '.'
        return None

def parse_way(text):
    """
    Just parse way identifier.
    """
    id = text[4:text.find('"', 6)]
    return {'id': int(id)}

def parse_relation(text):
    """
    Just parse relation identifier.
    """
    id = text[4:text.find('"', 6)]
    return {'id': int(id)}

def parse_member(text):
    """
    Parse member type, reference, and role.
    """
    if text[6] == 'w':
        type = 'way'
    else:
        type = 'node'
    ref_index = text.find('ref')
    role_index = text.find('role')
    ref = text[ref_index + 5:text.find('"', ref_index + 7)]
    role = text[role_index + 6:text.find('"', role_index + 8)]
    return {'type': type, 'ref': int(ref), 'role': role}

def parse_tag(text):
    v_index = text.find('v="')
    k = text[3:text.find('"', 4)]
    v = text[v_index + 3:text.find('"', v_index + 4)]
    return k, v

def parse_osm_file(file_name, silent=False):
    if not silent:
        print 'Reading OSM file ' + file_name
    start_time = datetime.datetime.now()
    node_map = {}
    way_map = {}
    relation_map = {}
    with open(file_name) as f:
        for lines_number, l in enumerate(f):
            pass
    input_file = open(file_name)
    line = input_file.readline()
    line_number = 0
    while line != '':
        line_number += 1
        ui.write_line(line_number, lines_number)

        # Node parsing.

        if line[:6] in [' <node', '\t<node']:
            if line[-3] == '/':
                node = parse_node(line[7:-3])
                node_map[node['id']] = node
            else:
                element = parse_node(line[7:-2])
                element['tags'] = {}
        elif line in [' </node>\n', '\t</node>\n']:
            node_map[element['id']] = element

        # Way parsing.

        elif line[:5] in [' <way', '\t<way']:
            if line[-3] == '/':
                way = parse_way(line[6:-3])
                way_map[node['id']] = way
            else:
                element = parse_way(line[6:-2])
                element['tags'] = {}
                element['nodes'] = []
        elif line in [' </way>\n', '\t</way>\n']:
            way_map[element['id']] = element

        # Relation parsing.

        elif line[:10] in [' <relation', '\t<relation']:
            if line[-3] == '/':
                relation = parse_relation(line[11:-3])
                relation_map[relation['id']] = relation
            else:
                element = parse_relation(line[11:-2])
                element['tags'] = {}
                element['members'] = []
        elif line in [' </relation>\n', '\t</relation>\n']:
            relation_map[element['id']] = element

        # Elements parsing.

        elif line[:6] in ['  <tag', '\t\t<tag']:
            k, v = parse_tag(line[7:-3])
            element['tags'][k] = v
        elif line[:5] in ['  <nd', '\t\t<nd']:
            element['nodes'].append(int(line[11:-4]))
        elif line[:5] in ['  <member', '\t\t<member']:
            member = parse_member(line[10:-3])
            element['members'].append(member)
        line = input_file.readline()
    input_file.close()

    ui.write_line(-1, lines_number)  # Complete progress bar.

    if not silent:
        print 'File readed in ' + \
            str(datetime.datetime.now() - start_time) + '.'
        print 'Nodes: ' + str(len(node_map)) + ', ways: ' + \
            str(len(way_map)) + ', relations: ' + str(len(relation_map)) + '.'
    return node_map, way_map, relation_map
