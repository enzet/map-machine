"""
Author: Sergey Vartanov (me@enzet.ru).
"""

import sys

def write_line(number, total):
    if number == -1:
        print ('%3s' % '100') + ' %: [' + (100 * '=') + '].'
    elif number % 1000 == 0:
        p = number / float(total)
        l = int(p * 100)
        print ('%3s' % str(int(p * 1000) / 10)) + ' %: [' + (l * '=') + \
            ((100 - l) * ' ') + '].'
        sys.stdout.write("\033[F")

