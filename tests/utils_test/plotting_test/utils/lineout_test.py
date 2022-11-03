# -*- coding: utf-8 -*-
"""
Created the 03/11/2022

@author: Sebastien Weber
"""
import pyqtgraph as pg

import pytest
from pymodaq.utils.plotting.utils.lineout import curve_item_factory, COLOR_LIST, COLORS_DICT


@pytest.fixture
def init_qt(qtbot):
    return qtbot


class TestCurveFactory:
    @pytest.mark.parametrize('pen', list(COLORS_DICT.keys())+COLOR_LIST)
    def test_create_curve(self, init_qt, pen):
        curve = curve_item_factory(pen=pen)
        assert isinstance(curve, pg.PlotCurveItem)

    def test_wrong_pen(self, init_qt):
        with pytest.raises(ValueError):
            curve = curve_item_factory(pen='this is not a valid color key')


class TestLineoutPlotter:
    pass
