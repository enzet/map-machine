#!/usr/bin/env python

"""
Author: Sergey Vartanov (me@enzet.ru)
"""

import math
import sys

sys.path.append('lib')

from vector import Vector


class Flinger(object):
    """
    Flinger. Coordinates repositioning.
    """
    def __init__(self, minimum, maximum, target_minimum=None, target_maximum=None, ratio=None):
        self.minimum = minimum
        self.maximum = maximum

        if not target_minimum:
            target_minimum = Vector()
        if not target_maximum:
            target_maximum = maximum - minimum

        space = Vector()

        if ratio:
            if ratio == 'geo':
                ratio = math.sin((90.0 - ((self.maximum.y + self.minimum.y) / 2.0)) / 180.0 * math.pi)

            current_ratio = (self.maximum.x - self.minimum.x) * ratio / (self.maximum.y - self.minimum.y)
            target_ratio = (target_maximum.x - target_minimum.x) / (target_maximum.y - target_minimum.y)

            if current_ratio >= target_ratio:
                n = (target_maximum.x - target_minimum.x) / (maximum.x - minimum.x) / ratio
                space.y = ((target_maximum.y - target_minimum.y) - (maximum.y - minimum.y) * n) / 2.0
                space.x = 0
            else:
                n = (target_maximum.y - target_minimum.y) / (maximum.y - minimum.y)
                space.x = ((target_maximum.x - target_minimum.x) - (maximum.x - minimum.x) * n) / 2.0
                space.y = 0

        target_minimum.x += space
        target_maximum.x += space

        self.target_minimum = target_minimum
        self.target_maximum = target_maximum

    def fling(self, current):
        """
        Fling current point to the surface.
        """
        x = map_(current.x, self.minimum.x, self.maximum.x, self.target_minimum.x, self.target_maximum.x)
        y = map_(current.y, self.minimum.y, self.maximum.y, self.target_minimum.y, self.target_maximum.y)
        return Vector(x, y)


class Geo:
    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon
    def __add__(self, other):
        return Geo(self.lat + other.lat, self.lon + other.lon)
    def __sub__(self, other):
        return Geo(self.lat - other.lat, self.lon - other.lon)
    def __repr__(self):
        return `self.lat` + ', ' + `self.lon`


class GeoFlinger:
    def __init__(self, minimum, maximum, target_minimum=None, target_maximum=None):
        self.minimum = minimum
        self.maximum = maximum

        # Ratio is depended of latitude. It is always <= 1.
        # In one latitude degree is always 40 000 / 360 km.
        # In one current longitude degree is about 40 000 / 360 * ratio km.

        ratio = math.sin((90.0 - ((self.maximum.lat + self.minimum.lat) / 2.0)) / 180.0 * math.pi)

        # Longitude displayed as x.
        # Latitude displayed as y.

        # Ratio is x / y.

        space = Vector()
        current_ratio = (self.maximum.lon - self.minimum.lon) * ratio / (self.maximum.lat - self.minimum.lat)
        target_ratio = (target_maximum.x - target_minimum.x) / (target_maximum.y - target_minimum.y)

        if current_ratio >= target_ratio:
            n = (target_maximum.x - target_minimum.x) / (maximum.lon - minimum.lon) / ratio
            space.y = ((target_maximum.y - target_minimum.y) - (maximum.lat - minimum.lat) * n) / 2.0
            space.x = 0
        else:
            n = (target_maximum.y - target_minimum.y) / (maximum.lat - minimum.lat) * ratio
            space.x = ((target_maximum.x - target_minimum.x) - (maximum.lon - minimum.lon) * n) / 2.0
            space.y = 0

        self.target_minimum = target_minimum + space
        self.target_maximum = target_maximum - space

        self.space = space

    def fling(self, current):
        x = map_(current.lon, self.minimum.lon, self.maximum.lon, 
                 self.target_minimum.x, self.target_maximum.x)
        y = map_(self.maximum.lat + self.minimum.lat - current.lat, 
                 self.minimum.lat, self.maximum.lat, 
                 self.target_minimum.y, self.target_maximum.y)
        return Vector(x, y)


def map_(value, current_min, current_max, target_min, target_max):
    """
    Map current value in bounds of current_min and current_max to bounds of target_min and target_max.
    """
    return target_min + (value - current_min) / (current_max - current_min) * (target_max - target_min)
