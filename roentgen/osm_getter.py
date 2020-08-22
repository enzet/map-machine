import re
import sys

from roentgen.ui import error
from roentgen import network


USAGE: str = '<box coordinates: left,bottom,right,top>'


def main(boundary_box: str):
    result_file_name = 'map/' + boundary_box + '.xml'

    matcher = re.match('(?P<left>[0-9\\.-]*),(?P<bottom>[0-9\\.-]*),' + \
        '(?P<right>[0-9\\.-]*),(?P<top>[0-9\\.-]*)', boundary_box)

    if not matcher:
        error('invalid boundary box')
        return

    try:
        left = float(matcher.group('left'))
        bottom = float(matcher.group('bottom'))
        right = float(matcher.group('right'))
        top = float(matcher.group('top'))
    except Exception:
        error('parsing boundary box')
        return

    if left >= right:
        error('negative horizontal boundary')
        return
    if bottom >= top:
        error('negative vertical boundary')
        return
    if right - left > 0.5 or top - bottom > 0.5:
        error('box too big')
        return
    network.get_content('api.openstreetmap.org/api/0.6/map',
            {'bbox': boundary_box}, result_file_name, 'html', is_secure=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python ' + sys.argv[0] + ' ' + USAGE)
        sys.exit(0)

    main(sys.argv[1])
