# -*- coding: utf-8 -*-
"""
Created the 28/10/2022

@author: Sebastien Weber
"""
import numpy as np
import pytest
from pymodaq.utils import math_utils as mutils
from pymodaq.utils import data as data_mod


def test_Axis():
    ax = data_mod.Axis()
    assert 'data' in ax
    assert 'label' in ax
    assert 'units' in ax

    assert ax.label == ax['label']

    ax = data_mod.Axis(np.array([1, 2, 3, 5, 7]), 'a label', 'seconds')
    assert np.all(ax['data'] == np.array([1, 2, 3, 5, 7]))
    assert ax['label'] == 'a label'
    assert ax['units'] == 'seconds'

    ax = data_mod.Axis(label=None, units=None)
    assert ax['label'] == ''
    assert ax['units'] == ''

    with pytest.raises(TypeError):
        data_mod.Axis(10)
    with pytest.raises(TypeError):
        data_mod.Axis(label=10)
    with pytest.raises(TypeError):
        data_mod.Axis(units=10)


def test_NavAxis():
    navaxis_tmp = data_mod.NavAxis(nav_index=1)
    assert isinstance(navaxis_tmp, data_mod.NavAxis)
    assert navaxis_tmp['nav_index'] == 1
    with pytest.raises(ValueError):
        data_mod.NavAxis()


class TestData:
    def test_Data(self):
        name = 'data_test'
        x = mutils.linspace_step(1, 100, 1)
        y = mutils.linspace_step(0.01, 1, 0.01)
        data_test = data_mod.Data(name=name, x_axis=x, y_axis=y)
        assert isinstance(data_test, data_mod.Data)
        assert data_test['name'] == name
        assert data_test['x_axis'] == data_mod.Axis(data=x)
        assert data_test['y_axis'] == data_mod.Axis(data=y)

        x = data_mod.Axis(x)
        y = data_mod.Axis(y)
        kwargs = [1, 2.0, 'kwargs', True, None]
        data_test = data_mod.Data(name=name, x_axis=x, y_axis=y, kwargs=kwargs)
        assert data_test['x_axis'] == x
        assert data_test['y_axis'] == y
        assert data_test['kwargs'] == kwargs

        with pytest.raises(TypeError):
            data_mod.Data(name=None)
        with pytest.raises(TypeError):
            data_mod.Data(source=None)
        with pytest.raises(ValueError):
            data_mod.Data(source='source')

        with pytest.raises(TypeError):
            data_mod.Data(distribution=None)
        with pytest.raises(ValueError):
            data_mod.Data(distribution='distribution')

        with pytest.raises(TypeError):
            data_mod.Data(x_axis=10)
        with pytest.raises(TypeError):
            data_mod.Data(y_axis=10)

    def test_DataFromPlugins(self):
        data = [mutils.linspace_step(1, 100, 1), mutils.linspace_step(0.01, 1, 0.01)]
        nav_axes = ["test"]
        x_axis = data_mod.Axis(data=mutils.linspace_step(1, 100, 1))
        y_axis = data_mod.Axis(data=mutils.linspace_step(1, 100, 1))
        data_test = data_mod.DataFromPlugins(data=data, nav_axes=nav_axes, nav_x_axis=x_axis, nav_y_axis=y_axis)
        assert isinstance(data_test, data_mod.DataFromPlugins)
        assert data_test['data'] == data
        assert data_test['nav_axes'] == nav_axes
        assert data_test['nav_x_axis'] == x_axis
        assert data_test['nav_y_axis'] == y_axis
        assert data_test['dim'] == 'Data1D'
        data = [np.array([1])]
        data_test = data_mod.DataFromPlugins(data=data)
        assert data_test['dim'] == 'Data0D'
        data = [np.array([[1, 1], [1, 2]])]
        data_test = data_mod.DataFromPlugins(data=data)
        assert data_test['dim'] == 'Data2D'
        data = [np.array([[[1, 1], [1, 2]], [[2, 1], [2, 2]]])]
        data_test = data_mod.DataFromPlugins(data=data)
        assert data_test['dim'] == 'DataND'

        with pytest.raises(TypeError):
            data_mod.DataFromPlugins(data=[1, 2, 3, 4, 5])
        with pytest.raises(TypeError):
            data_mod.DataFromPlugins(data="str")

    def test_DataToExport(self):
        data = np.array([1])
        data_test = data_mod.DataToExport(data=data)
        assert isinstance(data_test, data_mod.DataToExport)
        assert data_test['data'] == data
        assert data_test['dim'] == 'Data0D'
        data_test = data_mod.DataToExport()
        assert data_test['dim'] == 'Data0D'
        data = np.array([1, 1])
        data_test = data_mod.DataToExport(data=data)
        assert data_test['dim'] == 'Data1D'
        data = np.array([[1, 1], [1, 2]])
        data_test = data_mod.DataToExport(data=data)
        assert data_test['dim'] == 'Data2D'
        data = np.array([[[1, 1], [1, 2]], [[2, 1], [2, 2]]])
        data_test = data_mod.DataToExport(data=data)
        assert data_test['dim'] == 'DataND'

        with pytest.raises(TypeError):
            data_mod.DataToExport(data="data")


def test_ScaledAxis():
    scaled_axis = data_mod.ScaledAxis()
    assert isinstance(scaled_axis, data_mod.ScaledAxis)
    assert scaled_axis['offset'] == 0
    assert scaled_axis['scaling'] == 1

    with pytest.raises(TypeError):
        data_mod.ScaledAxis(offset=None)
    with pytest.raises(TypeError):
        data_mod.ScaledAxis(scaling=None)
    with pytest.raises(ValueError):
        data_mod.ScaledAxis(scaling=0)

    assert scaled_axis['scaling'] == scaled_axis.scaling


def test_ScalingOptions():
    scaling_options = data_mod.ScalingOptions(data_mod.ScaledAxis(), data_mod.ScaledAxis())
    assert isinstance(scaling_options, data_mod.ScalingOptions)
    assert isinstance(scaling_options['scaled_xaxis'], data_mod.ScaledAxis)
    assert isinstance(scaling_options['scaled_yaxis'], data_mod.ScaledAxis)

