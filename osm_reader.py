"""
Reading OpenStreetMap data from XML file.

Author: Sergey Vartanov
"""


def parse_node_full(text):
    """
    Parse full node parameters using regular expressions: id, visible, version, 
    etc. For faster parsing use parse_node().
    """
    m = re.match('id="(.*)" visible="(.*)" version="(.*)" changeset="(.*)" timestamp="(.*)" user="(.*)" uid="(.*)" lat="(.*)" lon="(.*)"', text)
    if m:
        return {'id': m.group(1), 'visible': m.group(2), 'changeset': m.group(3), 'timestamp': m.group(4), 'user': m.group(5), 'uid': m.group(6), 'lat': m.group(7), 'lon': m.group(8)}
    else:
        print 'Error node'

def parse_node(text):
    """
    Parse just identifier, latitude, and longitude from node parameters.
    """
    id = text[4:text.find('"', 6)]
    lat_index = text.find('lat')
    lon_index = text.find('lon')
    lat = text[lat_index + 5:text.find('"', lat_index + 7)]
    lon = text[lon_index + 5:text.find('"', lon_index + 7)]
    return {'id': id, 'lat': lat, 'lon': lon}

def parse_way_full(text):
    m = re.match('id="(.*)" visible="(.*)" version="(.*)" changeset="(.*)" timestamp="(.*)" user="(.*)" uid="(.*)"', text)
    if m:
        return {'id': m.group(1), 'visible': m.group(2), 'changeset': m.group(3), 'timestamp': m.group(4), 'user': m.group(5), 'uid': m.group(6)}
    else:
        print 'Error way'

def parse_way(text):
    id = text[4:text.find('"', 6)]
    return {'id': id}

def parse_tag(text):
    v_index = text.find('v="')
    k = text[3:text.find('"', 4)]
    v = text[v_index + 3:text.find('"', v_index + 4)]
    return k, v

def get_max_min(nodes):
	maximum = Geo(nodes[0]['lon'], nodes[0]['lat'])
	minimum = Geo(nodes[0]['lon'], nodes[0]['lat'])
	for node in nodes:
		if node['lat'] > maximum.lat: maximum.lat = node['lat']
		if node['lat'] < minimum.lat: minimum.lat = node['lat']
		if node['lon'] > maximum.lon: maximum.lon = node['lon']
		if node['lon'] < minimum.lon: minimum.lon = node['lon']
	return minimum, maximum

def parse_osm_file(file_name, silent=False):
    if not silent:
        print 'Reading OSM file ' + file_name
	start_time = datetime.datetime.now()
	node_map = {}
	way_map = {}
	input_file = open(file_name)
	line = input_file.readline()
	while line != '':
		if line[:6] == ' <node':
			if line[-3] == '/':
				node = parse_node(line[7:-3])
				node_map[node['id']] = node
			else:
				element = parse_node(line[7:-2])
				element['tags'] = {}
		elif line == ' </node>':
			node_map[node['id']] = element
		elif line[:5] == ' <way':
			if line[-3] == '/':
				way = parse_node(line[7:-3])
				node_map[node['id']] = node
			else:
				element = parse_way(line[6:-2])
				element['tags'] = {}
				element['nodes'] = []
		elif line[:6] == '  <tag':
			k, v = parse_tag(line[7:-3])
			element['tags'][k] = v
		elif line[:5] == '  <nd':
			element['nodes'].append(line[11:-3])
		line = input_file.readline()
	input_file.close()
    if not silent:
        print 'File readed in ' + \
                str(datetime.datetime.now() - start_time) + '.'
	return node_map, way_map


