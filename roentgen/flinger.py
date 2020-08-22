#!/usr/bin/env python

"""
Author: Sergey Vartanov (me@enzet.ru)
"""

import math
import numpy as np


class Flinger(object):
    """
    Flinger. Coordinates repositioning.
    """
    def __init__(self, minimum, maximum, target_minimum=None, target_maximum=None, ratio=None):
        self.minimum = minimum
        self.maximum = maximum

        if not target_minimum:
            target_minimum = [0, 0]
        if not target_maximum:
            target_maximum = maximum - minimum

        space = [0, 0]

        if ratio:
            if ratio == 'geo':
                ratio = math.sin((90.0 - ((self.maximum[1] + self.minimum[1]) / 2.0)) / 180.0 * math.pi)

            current_ratio = (self.maximum[0] - self.minimum[0]) * ratio / (self.maximum[1] - self.minimum[1])
            target_ratio = (target_maximum[0] - target_minimum[0]) / (target_maximum[1] - target_minimum[1])

            if current_ratio >= target_ratio:
                n = (target_maximum[0] - target_minimum[0]) / (maximum[0] - minimum[0]) / ratio
                space[1] = ((target_maximum[1] - target_minimum[1]) - (maximum[1] - minimum[1]) * n) / 2.0
                space[0] = 0
            else:
                n = (target_maximum[1] - target_minimum[1]) / (maximum[1] - minimum[1])
                space[0] = ((target_maximum[0] - target_minimum[0]) - (maximum[0] - minimum[0]) * n) / 2.0
                space[1] = 0

        target_minimum[0] += space
        target_maximum[0] += space

        self.target_minimum = target_minimum
        self.target_maximum = target_maximum

    def fling(self, current):
        """
        Fling current point to the surface.
        """
        x = map_(current[0], self.minimum[0], self.maximum[0], self.target_minimum[0], self.target_maximum[0])
        y = map_(current[1], self.minimum[1], self.maximum[1], self.target_minimum[1], self.target_maximum[1])
        return [x, y]


class Geo:
    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon

    def __add__(self, other):
        return Geo(self.lat + other.lat, self.lon + other.lon)

    def __sub__(self, other):
        return Geo(self.lat - other.lat, self.lon - other.lon)

    def __repr__(self):
        return f"{self.lat}, {self.lon}"


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

        space = [0, 0]
        current_ratio = (self.maximum.lon - self.minimum.lon) * ratio / (self.maximum.lat - self.minimum.lat)
        target_ratio = (target_maximum[0] - target_minimum[0]) / (target_maximum[1] - target_minimum[1])

        if current_ratio >= target_ratio:
            n = (target_maximum[0] - target_minimum[0]) / (maximum.lon - minimum.lon) / ratio
            space[1] = ((target_maximum[1] - target_minimum[1]) - (maximum.lat - minimum.lat) * n) / 2.0
            space[0] = 0
        else:
            n = (target_maximum[1] - target_minimum[1]) / (maximum.lat - minimum.lat) * ratio
            space[0] = ((target_maximum[0] - target_minimum[0]) - (maximum.lon - minimum.lon) * n) / 2.0
            space[1] = 0

        self.target_minimum = np.add(target_minimum, space)
        self.target_maximum = np.subtract(target_maximum, space)

        self.space = space

    def fling(self, current):
        x = map_(current.lon, self.minimum.lon, self.maximum.lon, 
                 self.target_minimum[0], self.target_maximum[0])
        y = map_(self.maximum.lat + self.minimum.lat - current.lat, 
                 self.minimum.lat, self.maximum.lat, 
                 self.target_minimum[1], self.target_maximum[1])
        return [x, y]


def map_(value, current_min, current_max, target_min, target_max):
    """
    Map current value in bounds of current_min and current_max to bounds of target_min and target_max.
    """
    return target_min + (value - current_min) / (current_max - current_min) * (target_max - target_min)
