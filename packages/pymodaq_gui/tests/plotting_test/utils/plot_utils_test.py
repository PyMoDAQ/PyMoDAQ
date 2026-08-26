# -*- coding: utf-8 -*-
"""
Created the 03/11/2022

@author: Sebastien Weber
"""
import pytest
import numpy as np

from qtpy import QtWidgets

from pymodaq_gui.plotting.utils.plot_utils import (Point, get_sub_segmented_positions,
                                                   display_in_dock, _next_free_col)
from pymodaq_gui.utils.dock import Dock, DockArea
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




class TestDisplayInDock:

    def test_reattach_reuses_freed_slot_without_overlap(self, qtbot):
        area = DockArea()
        dock = Dock('settings')
        area.addDock(dock)

        widgets = [QtWidgets.QWidget() for _ in range(3)]
        for w in widgets:
            display_in_dock(True, w, dock)

        # detach the middle widget, freeing its column
        dock.removeWidget(widgets[1], close=False)
        assert _next_free_col(dock) == 1

        # reattaching should take that freed slot, not overlap widgets[2]
        display_in_dock(True, widgets[1], dock)
        positions = {id(w): dock.layout.getItemPosition(dock.layout.indexOf(w))[:2]
                    for w in widgets}
        assert len(set(positions.values())) == len(widgets)
