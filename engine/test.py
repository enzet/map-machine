"""
Author: Sergey Vartanov (me@enzet.ru).
"""

import copy
import extract_icon
import process
import os
import sys
import yaml

tags_file_name = '../data/tags.yml'

scheme = yaml.load(open(tags_file_name))

sys.path.append('../lib')

import svg

icons_file_name = '../icons/icons.svg'
icon_grid_file_name = '../icon_grid.svg'

def draw_icon(icon):
    output_file.write('<path d="' + icon['path'] + '" ' + \
        'style="fill:#444444;stroke:none;' + \
        'stroke-width:3;stroke-linejoin:round;" ' + \
        'transform="translate(' + icon['x'] + ',' + icon['y'] + ')" />\n')


# Actions

step = 24

width = step * 10

extracter = extract_icon.IconExtractor(icons_file_name)

x = step / 2
y = step / 2

to_draw = []

for element in scheme['tags']:
    if 'icon' in element:
        if not (set(element['icon']) in to_draw):
            to_draw.append(set(element['icon']))
    if 'add_icon' in element:
        if not (set(element['add_icon']) in to_draw):
            to_draw.append(set(element['add_icon']))
    if 'over_icon' in element:
        with_icons = []
        if 'under_icon' in element:
            for icon in element['under_icon']:
                if not (set([icon] + element['over_icon']) in to_draw):
                    to_draw.append(set([icon] + element['over_icon']))
        if 'under_icon' in element and 'with_icon' in element:
            for icon in element['under_icon']:
                for icon2 in element['with_icon']:
                    if not (set([icon] + [icon2] + element['over_icon']) in to_draw):
                        to_draw.append(set([icon] + [icon2] + element['over_icon']))
                for icon2 in element['with_icon']:
                    for icon3 in element['with_icon']:
                        if icon2 != icon3 and icon2 != icon and icon3 != icon:
                            if not (set([icon] + [icon2] + [icon3] + element['over_icon']) in to_draw):
                                to_draw.append(set([icon] + [icon2] + [icon3] + element['over_icon']))

icons = []
height = 24
number = 0

for icons_to_draw in to_draw:
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
        number += 1
        x += step
        if x > width - 8:
            x = step / 2
            y += step
            height += step

output_file = svg.SVG(open(icon_grid_file_name, 'w+'))
output_file.begin(width, height)

for icon in icons:
    draw_icon(icon)

print 'Icons: ' + str(number) + '.'

output_file.end()
