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
from pymodaq.utils import data as data_mod

LABEL = 'A Label'
UNITS = 'units'
DATA = np.linspace(0, 10, 11)

DATA0D = np.array([0.])
DATA1D = np.zeros((10,))
DATA2D = np.zeros((5, 6))
DATAND = np.zeros((5, 6, 3))



def init_axis(data=None, index=0):
    if data is None:
        data = DATA
    return data_mod.Axis(label=LABEL, units=UNITS, data=data, index=index)


def init_data(data=None, Ndata=1, axes=[], name='myData') -> data_mod.DataWithAxes:
    if data is None:
        data = DATA2D
    return data_mod.DataWithAxes(name, data_mod.DataSource(0), data=[data for ind in range(Ndata)],
                                 axes=axes)


@pytest.fixture()
def init_axis_fixt():
    return init_axis()


@pytest.fixture()
def init_data_fixt():
    return init_data()


@pytest.fixture()
def ini_data_to_export():
    dat1 = init_data(data=DATA2D, Ndata=2, name='data2D')
    dat2 = init_data(data=DATA1D, Ndata=3, name='data1D')
    data = data_mod.DataToExport(name='toexport', data=[dat1, dat2])
    return dat1, dat2, data


class TestAxisBase:

    def test_errors(self):
        with pytest.raises(TypeError):
            data_mod.AxisBase(label=24)
        with pytest.raises(TypeError):
            data_mod.AxisBase(units=42)
        with pytest.raises(TypeError):
            data_mod.AxisBase(index=1.)
        with pytest.raises(ValueError):
            data_mod.AxisBase(index=-2)

    def test_attributes(self, init_axis_fixt):
        ax = init_axis_fixt
        assert hasattr(ax, 'data')
        assert ax.data == pytest.approx(DATA)
        assert hasattr(ax, 'label')
        assert ax.label == LABEL
        assert hasattr(ax, 'units')
        assert ax.units == UNITS
        assert hasattr(ax, 'index')
        assert ax.index == 0

    def test_getitem(self, init_axis_fixt):
        ax = init_axis_fixt
        assert ax.label is ax['label']
        assert ax.units is ax['units']
        assert ax.data is ax['data']
        assert ax.index is ax['index']

    def test_operation(self, init_axis_fixt):
        scale = 2
        offset = 100
        ax = init_axis_fixt
        ax_scaled = ax * scale
        ax_offset = ax + offset
        assert isinstance(ax_scaled, data_mod.AxisBase)
        assert isinstance(ax_offset, data_mod.AxisBase)

        assert ax_scaled.data == approx(ax.data * scale)
        assert ax_offset.data == approx(ax.data + offset)


class TestDataLowLevel:
    def test_init(self):
        data = data_mod.DataLowLevel('myData')
        assert hasattr(data, 'timestamp')
        assert hasattr(data, 'name')
        assert data.name == 'myData'

    def test_timestamp(self):
        t1 = time.time()
        data = data_mod.DataLowLevel('myData')
        t2 = time.time()
        assert t1 <= data.timestamp <= t2


class TestDataBase:
    def test_init(self):
        Ndata = 2
        data = data_mod.DataBase('myData', data_mod.DataSource(0), data=[DATA2D for ind in range(Ndata)])
        assert data.length == Ndata
        assert data.dim == data_mod.DataDim['Data2D']
        assert data.shape == DATA2D.shape
        assert data.size == DATA2D.size
        assert hasattr(data, 'timestamp')


    def test_labels(self):
        Ndata = 3
        labels = ['label0', 'label1']
        labels_auto = labels + ['CH02']
        data = data_mod.DataBase('myData', data_mod.DataSource(0), data=[DATA2D for ind in range(Ndata)])
        assert len(data.labels) == Ndata
        assert data.labels == [f'CH{ind:02d}' for ind in range(Ndata)]

        data = data_mod.DataBase('myData', data_mod.DataSource(0), data=[DATA2D for ind in range(Ndata)],
                                 labels=labels)
        assert len(data.labels) == Ndata
        assert data.labels == labels_auto

    def test_data_source(self):
        data = data_mod.DataBase('myData', 'calculated',  data=[DATA2D])
        assert data.source == data_mod.DataSource['calculated']

    @mark.parametrize("data_array, datadim", [(DATA0D, 'Data0D'), (DATA0D, data_mod.DataDim['Data0D']),
                                              (DATA0D, 'Data2D')])
    def test_get_dim(self, data_array, datadim):
        data = data_mod.DataBase('myData', data_mod.DataSource(0), data=[data_array], dim=datadim)
        assert data.dim == data_mod.DataDim['Data0D']  # force dim to reflect datashape

    def test_force_dim(self):
        with pytest.warns(UserWarning):
            data_mod.DataBase('myData', data_mod.DataSource(0), data=[DATA1D], dim='Data0D')

    def test_errors(self):
        with pytest.raises(TypeError):
            data_mod.DataBase()
        with pytest.raises(ValueError):
            data_mod.DataBase('myData')
        with pytest.raises(TypeError):
            data_mod.DataBase('myData', data_mod.DataSource(0))
        with pytest.warns(UserWarning):
            data = data_mod.DataBase('myData', data_mod.DataSource(0), data=DATA2D)  # only a ndarray
        assert len(data) == 1
        assert np.all(data.data[0] == approx(DATA2D))
        with pytest.warns(UserWarning):
            data = data_mod.DataBase('myData', data_mod.DataSource(0), data=12.4)  # only a numeric
        assert len(data) == 1
        assert isinstance(data.data[0], np.ndarray)
        assert data.data[0][0] == approx(12.4)

        with pytest.raises(data_mod.DataShapeError):
            data_mod.DataBase('myData', data_mod.DataSource(0), data=[DATA2D, DATA0D])  # list of different ndarray shape length
        with pytest.raises(TypeError):
            data_mod.DataBase('myData', data_mod.DataSource(0), data=['12', 5])  # list of non ndarray


class TestDataWithAxes:
    def test_init(self):
        Ndata = 2
        data = data_mod.DataWithAxes('myData', data_mod.DataSource(0), data=[DATA2D for ind in range(Ndata)])
        assert data.axes == []

    def test_axis(self):
        with pytest.raises(TypeError):
            init_data(DATA2D, 2, axes=[np.linspace(0, 10)])

    @mark.parametrize('index', [-1, 0, 1, 3])
    def test_axis_index(self, index):
        with pytest.raises(ValueError):
            init_data(DATA2D, 2, axes=[init_axis(np.zeros((DATA2D.shape[1],)), -1)])
        with pytest.warns(UserWarning):
            index = 0
            data = init_data(DATA2D, 2, axes=[init_axis(np.zeros((10,)), index)])
            assert len(data.get_axis_from_index(0)) == DATA2D.shape[index]

        index = 1
        data = init_data(DATA2D, 2, axes=[init_axis(np.zeros((DATA2D.shape[index],)), index)])
        assert len(data.get_axis_from_index(index)) == DATA2D.shape[index]

        with pytest.raises(IndexError):
            init_data(DATA2D, 2, axes=[init_axis(np.zeros((DATA2D.shape[1],)), 2)])

    def test_get_shape_from_index(self):
        index = 1
        data = init_data(DATA2D, 2, axes=[init_axis(np.zeros((DATA2D.shape[index],)), index)])

        assert data.get_shape_from_index(0) == DATA2D.shape[0]
        assert data.get_shape_from_index(1) == DATA2D.shape[1]
        with pytest.raises(IndexError):
            data.get_shape_from_index(-1)
        with pytest.raises(IndexError):
            data.get_shape_from_index(2)

    def test_get_axis_from_dim(self):

        index1 = 1
        axis = init_axis(np.zeros((DATA2D.shape[index1],)), index1)
        data = init_data(DATA2D, 2, axes=[axis])

        assert data.get_axis_from_index(index1) == axis
        index0 = 0
        axis = data.get_axis_from_index(index0)
        assert axis is None
        axis = data.get_axis_from_index(index0, create=True)
        assert len(axis) == data.get_shape_from_index(index0)


def test_data_from_plugins():
    Ndata = 2
    data = data_mod.DataFromPlugins('myData', data=[DATA2D for ind in range(Ndata)])
    assert isinstance(data, data_mod.DataWithAxes)
    assert data.source == data_mod.DataSource['raw']


def test_data_raw():
    Ndata = 2
    data = data_mod.DataRaw('myData', data=[DATA2D for ind in range(Ndata)])
    assert isinstance(data, data_mod.DataWithAxes)
    assert data.source == data_mod.DataSource['raw']


def test_data_from_plugins():
    Ndata = 2
    data = data_mod.DataFromPlugins('myData', data=[DATA2D for ind in range(Ndata)])
    assert isinstance(data, data_mod.DataWithAxes)
    assert data.source == data_mod.DataSource['raw']


def test_data_calculated():
    Ndata = 2
    data = data_mod.DataCalculated('myData', data=[DATA2D for ind in range(Ndata)])
    assert isinstance(data, data_mod.DataWithAxes)
    assert data.source == data_mod.DataSource['calculated']


def test_data_from_roi():
    Ndata = 2
    data = data_mod.DataFromRoi('myData', data=[DATA2D for ind in range(Ndata)])
    assert isinstance(data, data_mod.DataWithAxes)
    assert data.source == data_mod.DataSource['calculated']


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


class TestDataToExport:
    def test_init(self, ini_data_to_export):
        dat1, dat2, data = ini_data_to_export

        assert data.name == 'toexport'
        assert data.data == [dat1, dat2]
        assert len(data) == 2

    def test_data_type(self):
        with pytest.raises(TypeError):
            data_mod.DataToExport(name='toexport', data=[np.zeros((10,))])
        with pytest.raises(TypeError):
            data_mod.DataToExport(name='toexport', data=init_data())

        data_mod.DataToExport(name='toexport', data=[data_mod.DataFromRoi('mydata', data=[np.zeros((10,))])])

    def test_append(self, ini_data_to_export):
        dat1, dat2, data = ini_data_to_export

        data.append([dat1, dat2])
        assert data.data == [dat1, dat2]
        assert len(data) == 2

        dat3 = init_data(data=DATA0D, Ndata=1, name='data0D')
        data.append(dat3)
        assert len(data) == 3
        assert data.data == [dat1, dat2, dat3]

    def test_get_data_by_dim(self, ini_data_to_export):
        dat1, dat2, data = ini_data_to_export
        assert len(data.get_data_from_dim(data_mod.DataDim['Data0D'])) == 0

        dat3 = init_data(data=DATA0D, Ndata=1, name='data0D')
        data.append(dat3)
        assert isinstance(data.get_data_from_dim('Data0D'), data_mod.DataToExport)
        assert data.get_data_from_dim('Data0D').data == [dat3]
        assert data.get_data_from_dim(data_mod.DataDim['Data0D']).data == [dat3]

        assert data.get_data_from_dim(data_mod.DataDim['Data1D']).data == [dat2]
        assert data.get_data_from_dim(data_mod.DataDim['Data2D']).data == [dat1]

        dat4 = init_data(data=DATA2D, Ndata=1, name='data2Dbis')
        data.append(dat4)
        assert data.get_data_from_dim(data_mod.DataDim['Data2D']).data == [dat1, dat4]

    def test_get_data_by_name(self, ini_data_to_export):
        dat1, dat2, data = ini_data_to_export

        assert data.get_data_from_name('data2D') == dat1
        assert data.get_data_from_name('data1D') == dat2
        dat3 = init_data(data=DATA2D, Ndata=1, name='data2Dbis')
        data.append(dat3)
        assert data.get_data_from_name('data2Dbis') == dat3
        dat4 = init_data(data=DATA2D, Ndata=1, name='data2D')
        data.append(dat4)
        assert data.get_data_from_name('data2D') == dat4
        assert dat1 not in data.data

    def test_get_names(self, ini_data_to_export):
        dat1, dat2, data = ini_data_to_export
        assert data.get_names() == ['data2D', 'data1D']
        assert data.get_names('Data1D') == ['data1D']
        assert data.get_names('Data2D') == ['data2D']

        dat3 = init_data(data=DATA2D, Ndata=1, name='data2Dbis')
        data.append(dat3)
        assert data.get_names('data2d') == ['data2D', 'data2Dbis']