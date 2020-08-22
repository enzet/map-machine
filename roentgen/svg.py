"""
Very simple SVG library.

Author: Sergey Vartanov (me@enzet.ru)
"""

import math


class SVG:
    def __init__(self, file_):
        self.file = file_
        self.index = 0

    def begin(self, width, height):
        self.file.write('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n\n')
        self.file.write('''<svg version = "1.1" baseProfile = "full"
                        xmlns = "http://www.w3.org/2000/svg"
                        xmlns:xlink = "http://www.w3.org/1999/xlink"
                        xmlns:ev = "http://www.w3.org/2001/xml-events"
                        bgcolor = "#e5e9e6" width = "''' + str(width) +
                        '" height = "' + str(height) + '">\n')

    def end(self):
        self.file.write('</svg>\n')

    def path(self, path, color='black', width=1, fill='none', end='butt', id=None, color2=None,
             gx1=0, gy1=0, gx2=0, gy2=0, dash=None, dashoffset=None, opacity=1, transform=None):
        if color2:
            self.index += 1
            self.file.write('<defs><linearGradient id = "grad' + str(self.index) + '" x1 = "' + str(gx1) + '" y1 = "' +
                            str(gy1) + ' " x2 = "' + str(gx2) + '" y2 = "' + str(gy2) +
                            '" gradientUnits="userSpaceOnUse"> <stop style="stop-color:' + self.get_color(color) +
                            ';stop-opacity:1;" offset="0" /><stop style="stop-color:' + self.get_color(color2) +
                            ';stop-opacity:1;" offset="1" /></linearGradient></defs>\n')
        self.file.write('  <path d = "' + path + '" ')
        if id:
            self.file.write('id = "' + id + '" ')
        if transform:
            self.file.write('transform="' + transform + '" ')
        self.file.write('style = "')
        if not color2:
            self.file.write('stroke:' + self.get_color(color) + '; ')
        else:
            self.file.write('stroke:url(#grad' + str(self.index) + '); ')
        self.file.write('stroke-width:' + str(width) + '; ')
        self.file.write('fill:' + self.get_color(fill) + '; ')
        self.file.write('stroke-linecap:' + end + '; ')
        if opacity != 1:
            self.file.write('opacity:' + str(opacity) + '; ')
        if dash:
            self.file.write('stroke-dasharray:' + dash + '; ')
        if dashoffset:
            self.file.write('stroke-dashoffset:' + str(dashoffset) + '; ')
        self.file.write('" />\n')

    def line(self, x1, y1, x2, y2, width=1, color='black', end='butt', id=None, color2=None,
             gx1=None, gy1=None, gx2=None, gy2=None, dash=None, dashoffset=None, opacity=None):
        if color2:
            if not gx1:
                gx1 = x1
            if not gy1:
                gy1 = y1
            if not gx2:
                gx2 = x2
            if not gy2:
                gy2 = y2
            self.index += 1
            self.file.write('<defs><linearGradient id = "grad' + str(self.index) + '" x1 = "' + str(gx1) + '" y1 = "' + str(gy1) + '" x2 = "' + str(gx2) + '" y2 = "' + str(gy2) + '" gradientUnits="userSpaceOnUse">\n<stop\nstyle="stop-color:#' + str(color) + ';stop-opacity:1;"\noffset="0"\n /><stop\nstyle="stop-color:#' + str(color2) + ';stop-opacity:1;"\noffset="1"\n /></linearGradient>\n</defs>\n')
        self.file.write('  <path d = "M ' + str(x1) + ',' + str(y1) + ' ' + str(x2) + ',' + str(y2) + '" ')
        if id:
            self.file.write('id = "' + id + '" ')
        self.file.write('style = "')
        if not color2:
            self.file.write('stroke:' + self.get_color(color) + '; ')
        else:
            self.file.write('stroke:url(#grad' + str(self.index) + '); ')
        self.file.write('stroke-width:' + str(width) + '; ')
        self.file.write('stroke-linecap:' + end + '; ')
        if dash:
            self.file.write('stroke-dasharray:' + dash + '; ')
        if dashoffset:
            self.file.write('stroke-dashoffset:' + str(dashoffset) + '; ')
        if opacity:
            self.file.write('opacity: ' + str(opacity) + '; ')
        self.file.write('" />\n')

    def rect(self, x, y, width, height, color='black', id=None, rx=0, ry=0, opacity=1.0, stroke_color='none',
             stroke_width=1.0):
        self.file.write('  <rect x = "' + str(x) + '" y = "' + str(y) + '" rx = "' + str(rx) + '" ry = "' + str(ry) +
                        '" ')
        self.file.write(' width = "' + str(width) + '" height = "' + str(height) + '" ')
        if id:
            self.file.write('id = "' + id + '" ')
        self.file.write('style = "')
        if opacity != 1:
            self.file.write('opacity:' + str(opacity) + '; ')
        self.file.write('fill:' + self.get_color(color) + '; ')
        self.file.write('stroke:' + self.get_color(stroke_color) + '; ')
        self.file.write('stroke-width:' + str(stroke_width) + '; ')
        self.file.write('" />\n')

    def curve(self, x1, y1, x2, y2, x3, y3, x4, y4, id=None, width=1, color='black'):
        self.file.write('  <path d = "M ' + str(x1) + ',' + str(y1) + ' C ' + str(x2) + ',' + str(y2) + ' ')
        self.file.write(str(x3) + ',' + str(y3) + ' ' + str(x4) + ',' + str(y4) + '" ')
        self.file.write('style = "')
        self.file.write('stroke:' + self.get_color(color) + '; ')
        self.file.write('stroke-width:' + str(width) + '; ')
        self.file.write('fill: none; ')
        self.file.write('" />\n')

    def rhombus(self, x, y, width, height, color='black', id=None):
        self.file.write('''  <path d = "M %5.1f %5.1f L %5.1f %5.1f L %5.1f %5.1f
                L %5.1f %5.1f L %5.1f %5.1f" ''' % (x, y - height, x + width, y, x, y + height, x - width, y, x,
                                                    y - height))
        if id:
            self.file.write('id = "' + id + '" ')
        self.file.write('style = "')
        self.file.write('fill:' + self.get_color(color) + '; ')
        self.file.write('" />\n')

    def circle(self, x, y, d, color='black', color2='white', fill='none', 
            opacity=None, width=1, id=None, gx=0, gy=0, gr=0, fx=0, fy=0):
        is_grad = gx != 0 or gy != 0 or gr != 0
        if is_grad:
            self.index += 1
            self.file.write('''<defs>
                <radialGradient id="grad''' + str(self.index) + '" cx="' + str(gx) + '%" cy="' + str(gy) + '%" r="' + str(gr) + '%" fx="' + str(fx) + '%" fy="' + str(fy) + '''%">
                  <stop offset="0%" style="stop-color:rgb(255,255,255);
                  stop-opacity:0" />
                  <stop offset="100%" style="stop-color:''' + self.get_color(color) + ''';stop-opacity:1" />
                </radialGradient>
              </defs>''')
        c = 0.577
        self.file.write('''  <path d = "M %5.1f %5.1f C %5.1f %5.1f
                %5.1f %5.1f %5.1f %5.1f C %5.1f %5.1f %5.1f %5.1f %5.1f
                %5.1f C %5.1f %5.1f %5.1f %5.1f %5.1f %5.1f C %5.1f %5.1f
                %5.1f %5.1f %5.1f %5.1f" ''' % (
                x, y + d, x - d * c, y + d, x - d, y + d * c, x - d, y, x - d,
                y - d * c, x - d * c, y - d, x, y - d, x + d * c, y - d, x + d,
                y - d * c, x + d, y, x + d, y + d * c, x + d * c, y + d, x,
                y + d))
        if id:
            self.file.write('id = "' + id + '" ')
        self.file.write('style = "')
        if is_grad:
            self.file.write('fill:url(#grad' + str(self.index) + '); ')
        else:
            self.file.write('fill:' + self.get_color(fill) + '; ')
        self.file.write('stroke-width:' + str(width) + '; ')
        self.file.write('stroke:' + self.get_color(color) + '; ')
        if opacity:
            self.file.write('opacity:' + str(opacity) + '; ')
        self.file.write('" />\n')

    # text-align:center;text-anchor:middle
    # font-weight:bold;font-stretch:normal;text-align:start;line-height:125%;letter-spacing:2px;

    def text(self, x, y, text, font='Myriad Pro', size='10', align='left',
        color='black', id=None, weight=None, letter_spacing=None, angle=None,
        opacity=None):
        """
        Drawing SVG <text> element.
        """
        if angle is None:
            self.file.write('  <text x = "' + str(x) + '" y = "' + str(y) + '" ')
        else:
            self.file.write('  <text x = "0" y = "0" ')
        self.file.write('font-size = "' + str(size) + '" ')
        if id:
            self.file.write('id = "' + id + '" ')
        if not (angle is None) and angle <= 0:
            align = 'end'
        if align == 'right':
            align = 'end'
        if align == 'center':
            align = 'middle'
        self.file.write('style = "')
        self.file.write('text-anchor:' + align + '; ')
        if opacity:
            self.file.write('opacity:' + str(opacity) + '; ')
        self.file.write('font-family: ' + font + '; ')
        self.file.write('fill: ' + self.get_color(color) + '; ')
        if weight == 'bold':
            self.file.write('font-weight:bold; ')
        if letter_spacing:
            self.file.write('letter-spacing:' + str(letter_spacing) + '; ')
        self.file.write('"')
        if not (angle is None):
            if math.sin(angle) > 0:
                trans = 'transform = "matrix(' + str(math.sin(angle)) + ',' + str(math.cos(angle)) + ',' + \
                        str(-math.cos(angle)) + ',' + str(math.sin(angle)) + ',' + str(x) + ',' + str(y) + ')"'
            else:
                trans = 'transform = "matrix(' + str(math.sin(angle + math.pi)) + ',' + str(math.cos(angle + math.pi)) + ',' + \
                        str(-math.cos(angle + math.pi)) + ',' + str(math.sin(angle + math.pi)) + ',' + str(x) + ',' + str(y) + ')"'
            self.file.write(' ' + trans)
        self.file.write('>')
        self.file.write(text)
        self.file.write('</text>\n')

    @staticmethod
    def get_color(color):
        if color == 'none':
            return 'none'
        if color == 'black':
            return 'black'
        return '#' + str(color)

    def begin_layer(self, name):
        self.file.write('<g id="' + name + '" label="' + name + '" ')
        self.file.write('inkscape:groupmode="layer">\n')

    def end_layer(self):
        self.file.write('</g>\n')

    def write(self, raw_code):
        self.file.write(raw_code)
