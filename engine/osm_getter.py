import re
import sys

sys.path.append('../lib')

import network

usage = '<box coordinates: left,bottom,right,top>'

if len(sys.argv) < 2:
    print 'Usage: python ' + sys.argv[0] + ' ' + usage
    sys.exit(0)

boundary_box = sys.argv[1]

result_file_name = '../map/' + boundary_box + '.xml'

matcher = re.match('(?P<left>[0-9\\.-]*),(?P<bottom>[0-9\\.-]*),' + \
    '(?P<right>[0-9\\.-]*),(?P<top>[0-9\\.-]*)', boundary_box)

def error(message=None):
    if message:
        print 'Error: ' + message + '.'
    else:
        print 'Error.'
    sys.exit(1)

if not matcher:
    error('invalid boundary box')
else:
    try:
        left = float(matcher.group('left'))
        bottom = float(matcher.group('bottom'))
        right = float(matcher.group('right'))
        top = float(matcher.group('top'))
    except Exception as e:
        error('parsing boundary box')
    if left >= right:
        error('negative horisontal boundary')
    if bottom >= top:
        error('negative vertical boundary')
    if right - left > 0.5 or top - bottom > 0.5:
        error('box too big')
    content = network.get_content('api.openstreetmap.org/api/0.6/map',
            {'bbox': boundary_box}, result_file_name, 'html')
