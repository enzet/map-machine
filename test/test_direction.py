"""
Test direction processing.

Author: Sergey Vartanov (me@enzet.ru).
"""
import numpy as np

from roentgen.direction import parse_vector


def test_compass_points_1():
    assert np.allclose(parse_vector("N"), np.array([0, -1]))


def test_compass_points_2():
    root: np.float64 = -np.sqrt(2) / 2
    assert np.allclose(parse_vector("NW"), np.array([root, root]))


def test_compass_points_3():
    assert np.allclose(
        parse_vector("SSW"), np.array([-0.38268343, 0.92387953]))


def test_wrong():
    assert not parse_vector("O")


def test_degree():
    assert np.allclose(parse_vector("90"), np.array([1, 0]))
