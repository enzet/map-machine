import copy
import extract_icon
import sys
import yaml

scheme = yaml.load(open('tags.yml'))

sys.path.append('lib')

import svg

step = 24

width = step * 10

extracter = extract_icon.IconExtractor('icons.svg')

output_file = svg.SVG(open('icon_grid.svg', 'w+'))
output_file.begin(width, 1000)

x = step / 2
y = step / 2

def get_icon(tags):
    print '--------------', tags
    main_icon = None
    extra_icons = []
    for element in scheme['tags']:
        matched = True
        for tag in element['tags']:
            if not tag in tags:
                matched = False
                break
            if element['tags'][tag] != '*' and element['tags'][tag] != tags[tag]:
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
        print '----', [main_icon] + extra_icons
        return [main_icon] + extra_icons
    else:
        print '----', []
        return []

to_draw = {}

for element in scheme['tags']:
    if 'icon' in element:
        to_draw[','.join(element['icon'])] = element['icon']
    if 'add_icon' in element:
        to_draw[','.join(element['add_icon'])] = element['add_icon']
    if 'over_icon' in element:
        for icon in element['under_icon']:
            to_draw[','.join([icon] + element['over_icon'])] = [icon] + element['over_icon']

for icon_key in to_draw.keys():
    icons = to_draw[icon_key]
    drawed = False
    for icon in icons:
        path, xx, yy = extracter.get_path(icon)
        if path:
            output_file.write('<path d="' + path + '" ' + \
                'style="fill:#444444;stroke:none;' + \
                'stroke-width:3;stroke-linejoin:round;" ' + \
                'transform="translate(' + \
                str(x - 8.0 - xx * 16) + ',' + \
                str(y - 8.0 - yy * 16) + ')" />\n')
            drawed = True
        else:
            print '\033[31m' + icon + '\033[0m'
    if drawed:
        x += step
        if x > width - 8:
            x = step / 2
            y += step

output_file.end()
