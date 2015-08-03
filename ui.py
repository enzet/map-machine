# -*- coding: utf-8 -*- from __future__ import unicode_literals

"""
Author: Sergey Vartanov (me@enzet.ru).
"""

import sys


def parse_options(args):
    options = {'draw_nodes': True, 'draw_ways': False, 'overlap': 12, 
               'show_missed_tags': False}
    args = iter(args[1:])
    for arg in args:
        if arg in ['-i', '--input']:
            options['input_file_name'] = next(args)
        elif arg in ['-o', '--output']:
            options['output_file_name'] = next(args)
        elif arg in ['-bbox', '--boundary-box']:
            arg = next(args)
            options['boundary_box'] = map(lambda x: float(x), arg.split(','))
        elif arg in ['-n', '--draw-nodes']:
            options['draw_nodes'] = True
        elif arg in ['-w', '--draw-ways']:
            options['draw_ways'] = True
        elif arg in ['-nn', '--no-draw-nodes']:
            options['draw_nodes'] = False
        elif arg in ['-nw', '--no-draw-ways']:
            options['draw_ways'] = False
        elif arg in ['--show-missed-tags']:
            options['show_missed_tags'] = True
        elif arg in ['--overlap']:
            options['overlap'] = int(next(args))
        else:
            print 'Unknown option: ' + arg
            return None
    return options


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

