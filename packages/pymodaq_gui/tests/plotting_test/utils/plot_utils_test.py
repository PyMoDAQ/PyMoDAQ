# -*- coding: utf-8 -*-
"""
Created the 03/11/2022

@author: Sebastien Weber
"""
import pytest
import numpy as np

from pyqtgraph.functions import mkColor

from pymodaq_gui.plotting.utils.plot_utils import (Point, Vector, get_sub_segmented_positions,
                                                   RoiInfo, RectROI, LinearROI)
from pymodaq_utils.math_utils import linspace_step


class TestPoint:
    def test_ini(self):
        coordinates = 12
        p = Point(coordinates)
        assert np.allclose(coordinates, p._coordinates)
        assert len(p) == 1

        coordinates = [12, 34, 21.2, 10]
        p = Point(*coordinates)
        assert np.allclose(coordinates, p._coordinates)
        assert len(p) == len(coordinates)

        coordinates = (12, 34, 21.2, 10)
        p = Point(coordinates)
        assert np.allclose(coordinates, p._coordinates)
        assert len(p) == len(coordinates)

        coordinates = np.array([12, 34, 21.2])
        p = Point(*coordinates)
        assert np.allclose(coordinates, p._coordinates)
        assert len(p) == len(coordinates)

        coordinates = np.array([12, 34, 21.2])
        p = Point(coordinates)
        assert np.allclose(coordinates, p._coordinates)
        assert len(p) == len(coordinates)

    def test_operation(self):
        p1_coordinates = np.array([12, 34, 21.2, 10])
        p1 = Point(*p1_coordinates)

        p2_coordinates = np.array([12, 34, 21.2])
        p2 = Point(*p2_coordinates)

        with pytest.raises(ValueError) as val:
            p2-p1

        p2_coordinates = np.array([12, 34, 21.2, 12.5])
        p2 = Point(p2_coordinates)

        p_plus = p1 + p2
        assert isinstance(p_plus, Point)
        assert np.allclose(p_plus.coordinates, p1_coordinates + p2_coordinates)

        p_minus = p1 - p2
        assert isinstance(p_minus, Point)
        assert np.allclose(p_minus.coordinates, p1_coordinates - p2_coordinates)


class TestVector:
    def test_init(self):
        pass


def test_get_sub_segmented_positions():
    start = 0
    stop = 2
    step = 0.15

    points = [Point(start), Point(stop)]
    positions = np.array(get_sub_segmented_positions(step, points))

    assert np.allclose(np.atleast_1d(np.squeeze(positions[:-1])), linspace_step(start, stop, step))

    points = [Point(0, 0), Point(1, 0), Point(1, -1), Point(0, 0)]
    positions = np.array(get_sub_segmented_positions(step, points))
    pass


class TestInfoFromROI:
    def test_ini(self):
        origin = Point(23)
        width = 40
        height = 25
        with pytest.raises(TypeError):
            roi_info = RoiInfo(origin)

        roi_info = RoiInfo(origin, width)

        assert isinstance(roi_info.origin, Point)
        assert roi_info.origin == origin

    def test_create_from_linear_roi(self, qtbot):
        pos_linear = [-30, 65]
        linear_color = (34, 78, 23)
        linear_roi = LinearROI(pos=pos_linear)
        linear_roi.setPen(linear_color)
        linear_roi_info = RoiInfo.info_from_linear_roi(linear_roi)

        assert linear_roi_info.origin == Point(pos_linear[0])
        assert linear_roi_info.size[0] == pytest.approx(pos_linear[1]-pos_linear[0])
        assert linear_roi_info.color == mkColor(linear_color)
        assert len(linear_roi_info.size) == 1
        assert linear_roi_info.roi_class == LinearROI

    def test_create_from_rect_roi(self, qtbot):
        pos = [-30, 65]
        size = [78, 5]
        color = (34, 78, 23)
        roi = RectROI(pos=pos, size=size)
        roi.setPen(color)
        roi_info = RoiInfo.info_from_rect_roi(roi)

        assert roi_info.origin == Point(pos[-1::-1])
        assert len(roi_info.size) == 2
        assert roi_info.size[0] == pytest.approx(size[1])  # ROI takes argument as (x, y) while
        # roi_info refers to the index of the numpy data (line, column, ...)
        assert roi_info.color == mkColor(color)
        assert roi_info.size[1] == pytest.approx(size[0])  # ROI takes argument as (x, y) while
        # roi_info refers to the index of the numpy data (line, column, ...)
        assert roi_info.roi_class == RectROI

    def test_get_repr(self, qtbot):
        pos = [-30, 65]
        size = [78, 5]
        color = (34, 78, 23)
        roi = RectROI(pos=pos, size=size)
        roi.setPen(color)
        roi_info = RoiInfo.info_from_rect_roi(roi)

        print(roi_info)

