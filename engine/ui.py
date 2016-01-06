# -*- coding: utf-8 -*- from __future__ import unicode_literals

"""
Author: Sergey Vartanov (me@enzet.ru).
"""

import argparse
import sys


def parse_options(args):

    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--input', dest='input_file_name',
                        required=True)
    parser.add_argument('-o', '--output', dest='output_file_name',
                        required=True)
    parser.add_argument('-bbox', '--boundary-box', dest='boundary_box',
                        required=True)
    parser.add_argument('-nn', '--no-draw-nodes', dest='draw_nodes',
                        action='store_false', default=True)
    parser.add_argument('-nw', '--no-draw-ways', dest='draw_ways',
                        action='store_false', default=True)
    parser.add_argument('-nc', '--no-draw-captions', dest='draw_captions',
                        action='store_false', default=True)
    parser.add_argument('--show-missed-tags', dest='show_missed_tags',
                        action='store_true')
    parser.add_argument('--no-show-missed-tags', dest='show_missed_tags',
                        action='store_false')
    parser.add_argument('--overlap', dest='overlap', default=12, type=int)
    parser.add_argument('-s', '--size', dest='size')
    parser.add_argument('--show-index', dest='show_index',
                        action='store_true')
    parser.add_argument('--no-show-index', dest='show_index',
                        action='store_false')
    parser.add_argument('--mode', dest='mode', default='normal')
    parser.add_argument('--seed', dest='seed', default='')
    parser.add_argument('--level', dest='level', default=None, type=float)

    arguments = parser.parse_args(args[1:])

    arguments.boundary_box = \
        map(lambda x: float(x.replace('m', '-')), arguments.boundary_box.split(','))
    arguments.size = map(lambda x: float(x), arguments.size.split(','))

    return arguments


def write_line(number, total):
    length = 20
    parts = length * 8
    boxes = [' ', '▏', '▎', '▍', '▌', '▋', '▊', '▉']

    if number == -1:
        print ('%3s' % '100') + ' % █' + (length * '█') + '█'
    elif number % 1000 == 0:
        p = number / float(total)
        l = int(p * parts)
        fl = l / 8
        pr = int(l - fl * 8)
        print ('%3s' % str(int(p * 1000) / 10)) + ' % █' + (fl * '█') + \
            boxes[pr] + ((length - fl - 1) * ' ') + '█'
        sys.stdout.write("\033[F")

