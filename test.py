"""
Author: Sergey Vartanov (me@enzet.ru).
"""

import copy
import extract_icon
import sys
import yaml

scheme = yaml.load(open('tags.yml'))

sys.path.append('lib')

import svg

def get_icon(tags):
    main_icon = None
    extra_icons = []
    for element in scheme['tags']:
        matched = True
        for tag in element['tags']:
            if not tag in tags:
                matched = False
                break
            if element['tags'][tag] != '*' and \
                    element['tags'][tag] != tags[tag]:
                matched = False
                break
        if matched:
            print 'matched', element
            if 'icon' in element:
                main_icon = copy.deepcopy(element['icon'])
            if 'over_icon' in element:
                main_icon += element['over_icon']
            if 'add_icon' in element:
                extra_icons += element['add_icon']
    if main_icon:
        return [main_icon] + extra_icons
    else:
        return []

def draw_icon(icon):
    output_file.write('<path d="' + icon['path'] + '" ' + \
        'style="fill:#444444;stroke:none;' + \
        'stroke-width:3;stroke-linejoin:round;" ' + \
        'transform="translate(' + icon['x'] + ',' + icon['y'] + ')" />\n')

# Actions

step = 24

width = step * 10

extracter = extract_icon.IconExtractor('icons.svg')

x = step / 2
y = step / 2

to_draw = {}

for element in scheme['tags']:
    if 'icon' in element:
        to_draw[','.join(element['icon'])] = element['icon']
    if 'add_icon' in element:
        to_draw[','.join(element['add_icon'])] = element['add_icon']
    if 'over_icon' in element:
        for icon in element['under_icon']:
            to_draw[','.join([icon] + element['over_icon'])] = [icon] + \
                element['over_icon']

icons = []
height = 24

for icon_key in to_draw.keys():
    icons_to_draw = to_draw[icon_key]
    drawed = False
    for icon in icons_to_draw:
        path, xx, yy = extracter.get_path(icon)
        if path:
            icons.append({'path': path, 
                'x': str(x - 8.0 - xx * 16), 
                'y': str(y - 8.0 - yy * 16)});
            drawed = True
        else:
            print '\033[31m' + icon + '\033[0m'
    if drawed:
        x += step
        if x > width - 8:
            x = step / 2
            y += step
            height += step

output_file = svg.SVG(open('icon_grid.svg', 'w+'))
output_file.begin(width, height)

for icon in icons:
    draw_icon(icon)

output_file.end()
