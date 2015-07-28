"""
Reading OpenStreetMap data from XML file.

Author: Sergey Vartanov
"""

import datetime


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
    input_file = open(file_name)
    line = input_file.readline()
    while line != '':

        # Node parsing.

        if line[:6] == ' <node':
            if line[-3] == '/':
                node = parse_node(line[7:-3])
                node_map[node['id']] = node
            else:
                element = parse_node(line[7:-2])
                element['tags'] = {}
        elif line == ' </node>\n':
            node_map[element['id']] = element

        # Way parsing.

        elif line[:5] == ' <way':
            if line[-3] == '/':
                way = parse_way(line[6:-3])
                node_map[node['id']] = node
            else:
                element = parse_way(line[6:-2])
                element['tags'] = {}
                element['nodes'] = []
        elif line == ' </way>\n':
            way_map[element['id']] = element

        # Relation parsing.

        elif line[:10] == ' <relation':
            if line[-3] == '/':
                relation = parse_relation(line[11:-3])
                relation_map[relation['id']] = relation
            else:
                element = parse_relation(line[11:-2])
                element['tags'] = {}
                element['members'] = []
        elif line == ' </relation>\n':
            relation_map[element['id']] = element

        # Elements parsing.

        elif line[:6] == '  <tag':
            k, v = parse_tag(line[7:-3])
            element['tags'][k] = v
        elif line[:5] == '  <nd':
            element['nodes'].append(int(line[11:-4]))
        elif line[:5] == '  <member':
            member = parse_member(line[10:-3])
            element['members'].append(member)
        line = input_file.readline()
    input_file.close()
    if not silent:
        print 'File readed in ' + \
                str(datetime.datetime.now() - start_time) + '.'
    return node_map, way_map, relation_map


