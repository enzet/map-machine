"""
Author: Sergey Vartanov (me@enzet.ru).
"""

import os
import random
import sys
import yaml

from roentgen import extract_icon

tags_file_name = '../data/tags.yml'

scheme = yaml.load(open(tags_file_name))

sys.path.append('../lib')

import svg

icons_file_name = '../icons/icons.svg'
icon_grid_file_name = '../icon_grid.svg'
icon_colors_file_name = '../data/icon_colors'


def draw_icon(icon, x, y, color='444444'):
    output_file.write('<path d="' + icon['path'] + '" ' + \
        'style="fill:#' + color + ';stroke:none;' + \
        'stroke-width:3;stroke-linejoin:round;" ' + \
        'transform="translate(' + str(icon['x'] + x) + ',' + str(icon['y'] + y) + ')" />\n')


# Actions

icon_colors = [('FFFFFF', '444444')]
if os.path.isfile(icon_colors_file_name):
    icon_colors_file = open(icon_colors_file_name)
    for line in icon_colors_file.read().split('\n'):
        background_color = hex(int(line[0:3]))[2:] + hex(int(line[3:6]))[2:] + \
                           hex(int(line[6:9]))[2:]
        foreground_color = hex(int(line[10:13]))[2:] + hex(int(line[13:16]))[2:] + \
                           hex(int(line[16:19]))[2:]
        icon_colors.append((background_color, foreground_color))

step = 24

width = 240

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

height = 24
number = 0

icons = []

for icons_to_draw in to_draw:
    drawed = False
    icon_set = {'icons': []}
    for icon in icons_to_draw:
        path, xx, yy = extracter.get_path(icon)
        if path:
            icon_set['icons'].append({'path': path, 
                'x': (- 8.0 - xx * 16), 
                'y': (- 8.0 - yy * 16)})
            drawed = True
        else:
            print('\033[31m' + icon + '\033[0m')
    if drawed:
        icons.append(icon_set)
        number += 1

height = (number / (width / step) + 1) * step

output_file = svg.SVG(open(icon_grid_file_name, 'w+'))
output_file.begin(width, height)

output_file.rect(0, 0, width, height, color='FFFFFF')

for icon in icons:
#for k in range(1000):
#    icon = random.choice(icons)
    background_color, foreground_color = random.choice(icon_colors)
    output_file.rect(x - 2 - 8, y - 2 - 8, 20, 20, color=background_color)
    for i in icon['icons']:
        draw_icon(i, x, y, foreground_color)
    x += step
    if x > width - 8:
        x = step / 2
        y += step
        height += step

print(f"Icons: {number}.")

output_file.end()
