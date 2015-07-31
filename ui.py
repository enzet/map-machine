# -*- coding: utf-8 -*- from __future__ import unicode_literals

"""
Author: Sergey Vartanov (me@enzet.ru).
"""

import sys

def write_line(number, total):
    length = 20

    if number == -1:
        print ('%3s' % '100') + ' % ░' + (length * '░') + '░'
    elif number % 1000 == 0:
        p = number / float(total)
        l = int(p * length)
        print ('%3s' % str(int(p * 1000) / 10)) + ' % ░' + (l * '░') + \
            ((length - l) * ' ') + '░'
        sys.stdout.write("\033[F")

