"""
Author: Sergey Vartanov (me@enzet.ru).
"""

import os
import random
import yaml

from roentgen import extract_icon
from roentgen.flinger import map_


def test_flinger_map():
    assert map_(5, 0, 10, 0, 20) == 10


def test_icons():
    tags_file_name = 'data/tags.yml'
    icons_file_name = 'icons/icons.svg'

    scheme = yaml.load(open(tags_file_name))

    extracter = extract_icon.IconExtractor(icons_file_name)

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

    for icons_to_draw in to_draw:
        icon_set = {'icons': []}
        for icon in icons_to_draw:
            path, xx, yy = extracter.get_path(icon)
            assert xx
            icon_set['icons'].append({'path': path, 
                'x': (- 8.0 - xx * 16), 
                'y': (- 8.0 - yy * 16)})
