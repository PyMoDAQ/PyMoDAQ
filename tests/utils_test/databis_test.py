# -*- coding: utf-8 -*-
"""
Created the 28/10/2022

@author: Sebastien Weber
"""

import numpy as np
import pytest
from pytest import approx, mark
import time

from pymodaq.utils import math_utils as mutils
from pymodaq.utils import databis as data_mod

LABEL = 'A Label'
UNITS = 'units'
DATA = np.linspace(0, 10, 11)

DATA0D = np.array([0.])
DATA1D = np.zeros((10,))
DATA2D = np.zeros((5, 6))
DATAND = np.zeros((5, 6, 3))


@pytest.fixture()
def init_axis():
    return data_mod.AxisBase(label=LABEL, units=UNITS, data=DATA)


class TestAxisBase:

    def test_errors(self):
        with pytest.raises(ValueError):
            data_mod.AxisBase()
        with pytest.raises(TypeError):
            data_mod.AxisBase(label=24)
        with pytest.raises(TypeError):
            data_mod.AxisBase(units=42)
        with pytest.raises(TypeError):
            data_mod.AxisBase(index=1.)
        with pytest.raises(ValueError):
            data_mod.AxisBase(index=-2)

    def test_attributes(self, init_axis):
        ax = init_axis
        assert hasattr(ax, 'data')
        assert ax.data == pytest.approx(DATA)
        assert hasattr(ax, 'label')
        assert ax.label == LABEL
        assert hasattr(ax, 'units')
        assert ax.units == UNITS
        assert hasattr(ax, 'index')
        assert ax.index == 0

    def test_getitem(self, init_axis):
        ax = init_axis
        assert ax.label is ax['label']
        assert ax.units is ax['units']
        assert ax.data is ax['data']
        assert ax.index is ax['index']

    def test_operation(self, init_axis):
        scale = 2
        offset = 100
        ax = init_axis
        ax_scaled = ax * scale
        ax_offset = ax + offset
        assert isinstance(ax_scaled, data_mod.AxisBase)
        assert isinstance(ax_offset, data_mod.AxisBase)

        assert ax_scaled.data == approx(ax.data * scale)
        assert ax_offset.data == approx(ax.data + offset)


class TestDataBase:

    def test_init(self):
        Ndata = 2
        data = data_mod.DataBase('myData', source=data_mod.DataSource(0), data=[DATA2D for ind in range(Ndata)])
        assert data.length == Ndata
        assert data.dim == data_mod.DataDim['Data2D']
        assert data.shape == DATA2D.shape
        assert data.size == DATA2D.size
        assert hasattr(data, 'timestamp')

    def test_data_source(self):
        data = data_mod.DataBase('myData', source='roi',  data=[DATA2D])
        assert data.source == data_mod.DataSource['roi']

    @mark.parametrize("data_array, datadim", [(DATA0D, 'Data0D'), (DATA0D, data_mod.DataDim['Data0D']),
                                              (DATA0D, 'Data2D')])
    def test_get_dim(self, data_array, datadim):
        data = data_mod.DataBase('myData', source=data_mod.DataSource(0), data=[data_array], dim=datadim)
        assert data.dim == data_mod.DataDim['Data0D']  # force dim to reflect datashape

    def test_force_dim(self):
        with pytest.warns(UserWarning):
            data = data_mod.DataBase('myData', source=data_mod.DataSource(0), data=[DATA1D], dim='Data0D')

    def test_timestamp(self):
        t1 = time.time()
        data = data_mod.DataBase('myData', source=data_mod.DataSource(0), data=[DATA1D])
        t2 = time.time()
        assert t1 <= data.timestamp <= t2

    def test_errors(self):
        with pytest.raises(TypeError):
            data_mod.DataBase('myData', source=data_mod.DataSource(0))
        with pytest.raises(TypeError):
            data_mod.DataBase('myData', source=data_mod.DataSource(0), data=DATA2D)  # only a ndarray
        with pytest.raises(data_mod.DataShapeError):
            data_mod.DataBase('myData', source=data_mod.DataSource(0), data=[DATA2D, DATA0D])  # list of different ndarray shape length
