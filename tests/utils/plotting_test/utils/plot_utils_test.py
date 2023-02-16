# -*- coding: utf-8 -*-
"""
Created the 03/11/2022

@author: Sebastien Weber
"""
import pytest
import numpy as np

from pymodaq.utils import data as data_mod
from pymodaq.utils.plotting.utils import plot_utils


class TestAxisInfo:
    def test_default(self):
        info = plot_utils.AxisInfos(label='mylabel', units='myunits')
        assert info.label == 'mylabel'
        assert info.units == 'myunits'
        assert info.scaling == 1
        assert info.offset == 0

    def test_type_error(self):
        with pytest.raises(TypeError):
            plot_utils.AxisInfos(label=12)
        with pytest.raises(TypeError):
            plot_utils.AxisInfos(units=12)
        with pytest.raises(TypeError):
            plot_utils.AxisInfos(scaling='12')
        with pytest.raises(TypeError):
            plot_utils.AxisInfos(scaling=np.complex(1, 45))
        with pytest.raises(TypeError):
            plot_utils.AxisInfos(offset='12')
        with pytest.raises(TypeError):
            plot_utils.AxisInfos(offset=np.complex(1, 45))


class TestExtractAxis:
    def test_info_data_is_None(self):
        axis = data_mod.Axis(label='mylabel', units='myunits')
        assert plot_utils.AxisInfosExtractor.extract_axis_info(axis) == plot_utils.AxisInfos(1, 0, 'mylabel', 'myunits')

    def test_info(self):
        axis = data_mod.Axis(label='mylabel', units='myunits', data=np.array([5, 20, 35]))
        assert plot_utils.AxisInfosExtractor.extract_axis_info(axis) == plot_utils.AxisInfos(15, 5, 'mylabel', 'myunits')

    def test_info_data_is_ndarray(self):
        axis = np.array([5, 20, 35])
        assert plot_utils.AxisInfosExtractor.extract_axis_info(axis) == plot_utils.AxisInfos(15, 5, '', '')

    def test_info_data_is_ndarray_scalingisneg(self):
        axis = np.array([35, 20, 5])
        assert plot_utils.AxisInfosExtractor.extract_axis_info(axis) == plot_utils.AxisInfos(-15, 35, '', '')

    def test_info_neg_scaling(self):
        axis = data_mod.Axis(label='mylabel', units='myunits', data=np.array([35, 20, 5]))
        assert plot_utils.AxisInfosExtractor.extract_axis_info(axis) == plot_utils.AxisInfos(-15, 35, 'mylabel', 'myunits')
