# -*- coding: utf-8 -*-
"""
Created the 28/10/2022

@author: Sebastien Weber
"""
import logging
import numpy as np
import pytest
from pytest import approx, mark
import time

from pymodaq.utils import math_utils as mutils
from pymodaq.utils import data as data_mod
from pymodaq.utils.data import DataDim


LABEL = 'A Label'
UNITS = 'units'
OFFSET = -20.4
SCALING = 0.22
SIZE = 20
DATA = OFFSET + SCALING * np.linspace(0, SIZE-1, SIZE)

DATA0D = np.array([2.7])
DATA1D = np.arange(0, 10)
DATA2D = np.arange(0, 5*6).reshape((5, 6))
DATAND = np.arange(0, 5 * 6 * 3).reshape((5, 6, 3))
Nn0 = 10
Nn1 = 5


def init_axis(data=None, index=0):
    if data is None:
        data = DATA
    return data_mod.Axis(label=LABEL, units=UNITS, data=data, index=index)


def init_data(data=None, Ndata=1, axes=[], name='myData', source=data_mod.DataSource['raw'],
              labels=None) -> data_mod.DataWithAxes:
    if data is None:
        data = DATA2D
    return data_mod.DataWithAxes(name, source, data=[data for ind in range(Ndata)],
                                 axes=axes, labels=labels)


def init_dataND():
    N0 = 5
    N1 = 6
    N2 = 3
    DATAND = np.arange(0, N0 * N1 * N2).reshape((N0, N1, N2))

    axis0 = data_mod.Axis(label='myaxis0', data=np.linspace(0, N0 - 1, N0), index=0)
    axis1 = data_mod.Axis(label='myaxis1', data=np.linspace(0, N1 - 1, N1), index=1)
    axis2 = data_mod.Axis(label='myaxis2', data=np.linspace(0, N2 - 1, N2), index=2)
    return data_mod.DataWithAxes('mydata', 'raw', data=[DATAND], axes=[axis0, axis1, axis2], nav_indexes=(0, 1)),\
           (N0, N1, N2)


@pytest.fixture()
def init_data_spread():
    Nspread = 21
    sig_axis = data_mod.Axis(label='signal', index=1, data=np.linspace(0, DATA1D.size - 1, DATA1D.size))
    nav_axis_0 = data_mod.Axis(label='nav0', index=0, data=np.random.rand(Nspread), spread_order=0)
    nav_axis_1 = data_mod.Axis(label='nav1', index=0, data=np.random.rand(Nspread), spread_order=1)

    data_array = np.array([ind / Nspread * DATA1D for ind in range(Nspread)])
    data = data_mod.DataRaw('mydata', distribution='spread', data=[data_array], nav_indexes=(0,),
                            axes=[nav_axis_0, sig_axis, nav_axis_1])
    return data, data_array, sig_axis, nav_axis_0, nav_axis_1, Nspread


@pytest.fixture()
def init_data_uniform() -> data_mod.DataWithAxes:

    nav_axis_0 = data_mod.Axis(label='nav0', index=0, data=np.linspace(0, Nn0 - 1, Nn0))
    nav_axis_1 = data_mod.Axis(label='nav1', index=1, data=np.linspace(0, Nn1 - 1, Nn1))
    sig_axis_0 = data_mod.Axis(label='signal0', index=2, data=np.linspace(0, DATA2D.shape[0] - 1, DATA2D.shape[0]))
    sig_axis_1 = data_mod.Axis(label='signal1', index=3, data=np.linspace(0, DATA2D.shape[1] - 1, DATA2D.shape[1]))

    data_array = np.ones((Nn0, Nn1, DATA2D.shape[0], DATA2D.shape[1]))
    data = data_mod.DataRaw('mydata', data=[data_array], nav_indexes=(0, 1),
                            axes=[nav_axis_0, sig_axis_0, nav_axis_1, sig_axis_1])
    return data


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


class TestDataDim:
    def test_index(self):
        dim = DataDim['Data0D']
        assert dim.dim_index == 0
        dim = DataDim['Data1D']
        assert dim.dim_index == 1
        dim = DataDim['Data2D']
        assert dim.dim_index == 2
        dim = DataDim['DataND']
        assert dim.dim_index == 3

    @pytest.mark.parametrize('dim1', ['Data0D', 'Data1D', 'Data2D', 'DataND'])
    @pytest.mark.parametrize('dim2', ['Data0D', 'Data1D', 'Data2D', 'DataND'])
    def test_comparison(self, dim1: str, dim2: str):
        assert (DataDim[dim1] < DataDim[dim2]) == (DataDim[dim1].dim_index < DataDim[dim2].dim_index)
        assert (DataDim[dim1] <= DataDim[dim2]) == (DataDim[dim1].dim_index <= DataDim[dim2].dim_index)
        assert (DataDim[dim1] > DataDim[dim2]) == (DataDim[dim1].dim_index > DataDim[dim2].dim_index)
        assert (DataDim[dim1] >= DataDim[dim2]) == (DataDim[dim1].dim_index >= DataDim[dim2].dim_index)

class TestAxis:

    def test_errors(self):
        with pytest.raises(TypeError):
            data_mod.Axis(label=24)
        with pytest.raises(TypeError):
            data_mod.Axis(units=42)
        with pytest.raises(TypeError):
            data_mod.Axis(index=1.)
        with pytest.raises(ValueError):
            data_mod.Axis(index=-2)

    def test_attributes(self, init_axis_fixt):
        ax = init_axis_fixt
        assert hasattr(ax, 'label')
        assert ax.label == LABEL
        assert hasattr(ax, 'units')
        assert ax.units == UNITS
        assert hasattr(ax, 'index')
        assert ax.index == 0
        assert hasattr(ax, 'data')
        assert ax.data is None
        assert ax.offset == pytest.approx(OFFSET)
        assert ax.scaling == pytest.approx(SCALING)

        data_tmp = np.array([0.1, 2, 23, 44, 21, 20])  # non linear axis
        ax = init_axis(data=data_tmp)
        assert np.all(ax.data == pytest.approx(data_tmp))
        assert ax.offset is None
        assert ax.scaling is None

    def test_operation(self, init_axis_fixt):
        scale = 2
        offset = 100
        ax = init_axis_fixt
        ax_scaled = ax * scale
        ax_offset = ax + offset
        assert isinstance(ax_scaled, data_mod.Axis)
        assert isinstance(ax_offset, data_mod.Axis)

        assert ax_scaled.scaling == approx(ax.scaling * scale)
        assert ax_offset.offset == approx(ax.offset + offset)

        data_tmp = np.array([0.1, 2, 23, 44, 21, 20])  # non linear axis
        ax = init_axis(data=data_tmp)
        ax_scaled = ax * scale
        ax_offset = ax + offset
        assert ax_scaled.data == approx(ax.data * scale)
        assert ax_offset.data == approx(ax.data + offset)

    def test_math(self, init_axis_fixt):
        ax = init_axis_fixt
        assert ax.mean() == pytest.approx(OFFSET + SIZE / 2 * SCALING)
        assert ax.min() == pytest.approx(OFFSET)
        assert ax.max() == pytest.approx(OFFSET + SIZE * SCALING)

        data_tmp = np.array([0.1, 2, 23, 44, 21, 20])  # non linear axis
        ax = init_axis(data=data_tmp)
        assert ax.mean() == pytest.approx(np.mean(data_tmp))
        assert ax.min() == pytest.approx(np.min(data_tmp))
        assert ax.max() == pytest.approx(np.max(data_tmp))

    def test_find_index(self, init_axis_fixt):
        ax = init_axis_fixt
        assert ax.find_index(0.01 + OFFSET + 4 * SCALING) == 4

        data_tmp = np.array([0.1, 2, 23, 44, 21, 20])  # non linear axis
        ax = init_axis(data=data_tmp)
        assert ax.find_index(5) == 1



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
        data = data_mod.DataBase('myData', data_mod.DataSource(0), data=[DATA1D], dim='Data0D')
        assert data.dim.name == 'Data1D'

    def test_errors(self):
        with pytest.raises(TypeError):
            data_mod.DataBase()
        with pytest.raises(ValueError):
            data_mod.DataBase('myData')
        with pytest.raises(TypeError):
            data_mod.DataBase('myData', data_mod.DataSource(0))
        data = data_mod.DataBase('myData', data_mod.DataSource(0), data=DATA2D)  # only a ndarray
        assert len(data) == 1
        assert np.all(data.data[0] == approx(DATA2D))
        data = data_mod.DataBase('myData', data_mod.DataSource(0), data=12.4)  # only a numeric
        assert len(data) == 1
        assert isinstance(data.data[0], np.ndarray)
        assert data.data[0][0] == approx(12.4)

        with pytest.raises(data_mod.DataShapeError):
            data_mod.DataBase('myData', data_mod.DataSource(0), data=[DATA2D, DATA0D])  # list of different ndarray shape length
        with pytest.raises(TypeError):
            data_mod.DataBase('myData', data_mod.DataSource(0), data=['12', 5])  # list of non ndarray

    def test_dunder(self):
        LENGTH = 24
        data = init_data(DATA0D, Ndata=LENGTH)
        assert len(data) == LENGTH
        count = 0
        for dat in data:
            assert np.all(dat == pytest.approx(DATA0D))
            count += 1
        assert count == len(data)

        assert np.all(DATA0D == pytest.approx(data[-1]))

        with pytest.raises(IndexError):
            data['str']
        with pytest.raises(IndexError):
            data[len(data) + 1]

    @pytest.mark.parametrize('datatmp', (DATA0D, DATA1D, DATA2D))
    def test_comparison_data_actuator(self, datatmp):
        LENGTH = 3
        data = init_data(datatmp, LENGTH)
        data_eq = init_data(datatmp, LENGTH)
        data_lt = init_data(datatmp - 0.01 * np.ones(datatmp.shape), LENGTH)
        data_gt = init_data(datatmp + 0.01 * np.ones(datatmp.shape), LENGTH)

        assert data == data_eq
        assert data >= data_eq
        assert data <= data_eq
        assert data > data_lt
        assert data < data_gt

    def test_comparison_numbers(self):
        LENGTH = 1
        data = init_data(DATA0D, LENGTH)
        data_eq = float(DATA0D[0])
        data_lt = float(DATA0D[0]) - 0.01
        data_gt = float(DATA0D[0]) + 0.01

        assert data == data_eq
        assert data >= data_eq
        assert data <= data_eq
        assert data > data_lt
        assert data < data_gt

        ARRAY = np.array([1, 2, 1.5])
        data = data_mod.DataActuator(data=[ARRAY])
        assert not data > 1
        assert data > 0.999
        assert data >= 1
        assert data == data_mod.DataActuator(data=[ARRAY])
        assert data < 2.001
        assert data <= 2

    def test_maths(self):
        data = init_data(data=DATA2D, Ndata=2)
        data1 = init_data(data=DATA2D, Ndata=2)

        data_sum = data + data1
        for ind_data in range(len(data)):
            assert np.all(data_sum[ind_data] == pytest.approx(2 * DATA2D))
        data_diff = data - data1
        for ind_data in range(len(data)):
            assert np.all(data_diff[ind_data] == pytest.approx(0 * DATA2D))

        data_mult = data * 0.85
        for ind_data in range(len(data)):
            assert np.all(data_mult[ind_data] == pytest.approx(0.85 * DATA2D))

        data_div = data / 0.85
        for ind_data in range(len(data)):
            assert np.all(data_div[ind_data] == pytest.approx(DATA2D/.85))

    def test_abs(self):
        data_p = init_data(data=DATA2D, Ndata=2)
        data_m = init_data(data=-DATA2D, Ndata=2)

        assert data_p.abs() == data_p
        assert data_m.abs() == data_p

    def test_average(self):
        WEIGHT = 5
        FRAC = 0.23
        data = init_data(data=DATA2D, Ndata=2)
        data1 = init_data(data=-DATA2D, Ndata=2)

        assert data.average(data1, 1) == data * 0
        assert data.average(data, 1) == data
        assert data.average(data, 2) == data

    def test_append(self):
        Ndata = 2
        labels = [f'label{ind}' for ind in range(Ndata)]
        Ndatabis = 3
        label_bis = [f'labelbis{ind}' for ind in range(Ndatabis)]
        data = init_data(data=DATA1D, Ndata=Ndata, labels=labels)
        data_bis = init_data(data=DATA1D, Ndata=Ndatabis, labels=label_bis)

        data.append(data_bis)
        assert len(data) == Ndata + Ndatabis
        assert data.labels == labels + label_bis


class TestDataWithAxesUniform:
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
        index = 0
        data = init_data(DATA2D, 2, axes=[init_axis(np.zeros((10,)), index)])
        assert len(data.get_axis_from_index(0)[0]) == DATA2D.shape[index]

        index = 1
        data = init_data(DATA2D, 2, axes=[init_axis(np.zeros((DATA2D.shape[index],)), index)])
        assert len(data.get_axis_from_index(index)[0]) == DATA2D.shape[index]

        with pytest.raises(IndexError):
            init_data(DATA2D, 2, axes=[init_axis(np.zeros((DATA2D.shape[1],)), 2)])

    def test_get_shape_from_index(self):
        index = 1
        data = init_data(DATA2D, 2, axes=[init_axis(np.zeros((DATA2D.shape[index],)), index)])

        assert data.axes_manager.get_shape_from_index(0) == DATA2D.shape[0]
        assert data.axes_manager.get_shape_from_index(1) == DATA2D.shape[1]
        with pytest.raises(IndexError):
            data.axes_manager.get_shape_from_index(-1)
        with pytest.raises(IndexError):
            data.axes_manager.get_shape_from_index(2)

    def test_get_axis_from_dim(self):

        index1 = 1
        axis = init_axis(np.zeros((DATA2D.shape[index1],)), index1)
        data = init_data(DATA2D, 2, axes=[axis])

        assert data.get_axis_from_index(index1)[0] == axis
        index0 = 0
        axis = data.get_axis_from_index(index0)[0]
        assert axis is None
        axis = data.get_axis_from_index(index0, create=True)[0]
        assert len(axis) == data.axes_manager.get_shape_from_index(index0)

    def test_deep_copy_with_new_data(self):
        data, shape = init_dataND()
        #on nav_indexes
        IND_TO_REMOVE = 1
        new_data = data.deepcopy_with_new_data([np.squeeze(dat[:, 0, :]) for dat in data.data],
                                               remove_axes_index=IND_TO_REMOVE)

        assert new_data.nav_indexes == (0,)
        assert new_data.sig_indexes == (1,)
        assert new_data.shape == np.squeeze(data.data[0][:, 0, :]).shape
        assert len(new_data.get_axis_indexes()) == 2
        assert data.get_axis_from_index(IND_TO_REMOVE)[0] not in new_data.axes

        # on sig_indexes
        IND_TO_REMOVE = 2
        new_data = data.deepcopy_with_new_data([np.squeeze(dat[:, :, 0]) for dat in data.data],
                                               remove_axes_index=IND_TO_REMOVE)

        assert new_data.nav_indexes == (0, 1)
        assert new_data.sig_indexes == ()
        assert new_data.shape == np.squeeze(data.data[0][:, :, 0]).shape
        assert len(new_data.get_axis_indexes()) == 2
        assert data.get_axis_from_index(IND_TO_REMOVE)[0] not in new_data.axes


        # on nav_indexes both axes
        IND_TO_REMOVE = [0, 1]
        new_data = data.deepcopy_with_new_data([np.squeeze(dat[0, 0, :]) for dat in data.data],
                                               remove_axes_index=IND_TO_REMOVE)

        assert new_data.nav_indexes == ()
        assert new_data.sig_indexes == (0,)
        assert new_data.shape == np.squeeze(data.data[0][0, 0, :]).shape
        assert len(new_data.get_axis_indexes()) == 1
        for ind in IND_TO_REMOVE:
            assert data.get_axis_from_index(ind)[0] not in new_data.axes

        # on all axes
        IND_TO_REMOVE = [0, 1, 2]
        new_data = data.deepcopy_with_new_data([np.atleast_1d(np.mean(dat)) for dat in data.data],
                                               remove_axes_index=IND_TO_REMOVE)

        assert new_data.nav_indexes == ()
        assert new_data.sig_indexes == (0,)
        assert new_data.shape == (1,)
        assert len(new_data.get_axis_indexes()) == 0
        for ind in IND_TO_REMOVE:
            assert data.get_axis_from_index(ind)[0] not in new_data.axes

    @pytest.mark.parametrize("IND_MEAN", [0, 1, 2])
    def test_mean(self, IND_MEAN):
        data, shape = init_dataND()
        new_data = data.mean(IND_MEAN)
        for ind, dat in enumerate(data):
            assert np.all(new_data[ind] == pytest.approx(np.mean(dat, IND_MEAN)))
        assert len(new_data.get_axis_indexes()) == 2


class TestNavIndexes:

    def test_set_nav_indexes(self):
        data, shape = init_dataND()

        assert data.shape == shape
        assert data.sig_indexes == (2,)

        data.nav_indexes = (1,)
        assert data.shape == shape
        assert data.nav_indexes == (1,)
        assert data.axes_manager.nav_indexes == (1,)
        assert data.sig_indexes == (0, 2)

        data.nav_indexes = ()
        assert data.sig_indexes == (0, 1,  2)


class TestDataWithAxesSpread:
    def test_init_data(self, init_data_spread):
        data, data_array, sig_axis, nav_axis_0, nav_axis_1, Nspread = init_data_spread
        data_mod.DataWithAxes(name='spread', source=data_mod.DataSource['raw'], dim=data_mod.DataDim['Data1D'],
                              distribution=data_mod.DataDistribution['spread'], data=[data_array],
                              nav_indexes=(0,),
                              axes=[sig_axis, nav_axis_0, nav_axis_1])

    def test_nav_index(self, init_data_spread):
        data, data_array, sig_axis, nav_axis_0, nav_axis_1, Nspread = init_data_spread
        with pytest.raises(ValueError):
            data_mod.DataWithAxes(name='spread', source=data_mod.DataSource['raw'], dim=data_mod.DataDim['Data1D'],
                                  distribution=data_mod.DataDistribution['spread'], data=[data_array],
                                  nav_indexes=(0, 1),
                                  axes=[sig_axis, nav_axis_0, nav_axis_1])

    def test_nav_axis_length(self, init_data_spread):
        data, data_array, sig_axis, nav_axis_0, nav_axis_1, Nspread = init_data_spread
        nav_axis_1.data = np.concatenate((nav_axis_1.data, np.array([0.1,])))
        with pytest.raises(data_mod.DataLengthError):
            data_mod.DataWithAxes(name='spread', source=data_mod.DataSource['raw'], dim=data_mod.DataDim['Data1D'],
                                  distribution=data_mod.DataDistribution['spread'], data=[data_array],
                                  nav_indexes=(0,),
                                  axes=[sig_axis, nav_axis_0, nav_axis_1])

    def test_compute_shape(self, init_data_spread):
        data, data_array, sig_axis, nav_axis_0, nav_axis_1, Nspread = init_data_spread
        assert data.axes_manager.compute_shape_from_axes() == data_array.shape

    def test_repr(self, init_data_spread):
        data, data_array, sig_axis, nav_axis_0, nav_axis_1, Nspread = init_data_spread
        assert data.axes_manager._get_dimension_str() == f'({nav_axis_1.size}|{sig_axis.size})'

    def test_deep_copy_with_new_data(self, init_data_spread):
        data, data_array, sig_axis, nav_axis_0, nav_axis_1, Nspread = init_data_spread

        #on nav_indexes
        IND_TO_REMOVE = 0
        new_data = data.deepcopy_with_new_data([np.squeeze(dat[0, :]) for dat in data.data],
                                               remove_axes_index=IND_TO_REMOVE)

        assert new_data.nav_indexes == ()
        assert new_data.sig_indexes == (0,)
        assert new_data.shape == np.squeeze(data.data[0][0, :]).shape
        assert len(new_data.get_axis_indexes()) == 1
        assert data.get_axis_from_index(IND_TO_REMOVE)[0] not in new_data.axes

        # on sig_indexes
        IND_TO_REMOVE = 1
        new_data = data.deepcopy_with_new_data([np.squeeze(dat[:, 0]) for dat in data.data],
                                               remove_axes_index=IND_TO_REMOVE)

        assert new_data.nav_indexes == (0,)
        assert new_data.sig_indexes == ()
        assert new_data.shape == np.squeeze(data.data[0][:, 0]).shape
        assert len(new_data.get_axis_indexes()) == 1
        assert data.get_axis_from_index(IND_TO_REMOVE)[0] not in new_data.axes

    @pytest.mark.parametrize("IND_MEAN", [0, 1])
    def test_mean(self, IND_MEAN, init_data_spread):
        data, data_array, sig_axis, nav_axis_0, nav_axis_1, Nspread = init_data_spread

        new_data = data.mean(IND_MEAN)
        for ind, dat in enumerate(data):
            assert np.all(new_data[ind] == pytest.approx(np.mean(dat, IND_MEAN)))
        assert len(new_data.get_axis_indexes()) == 1
        if IND_MEAN in data.nav_indexes:
            assert len(new_data.axes) == 1
        else:
            assert len(new_data.axes) == 2


class TestSlicingUniform:
    def test_slice_navigation(self, init_data_uniform):
        data_raw = init_data_uniform
        assert data_raw.shape == (Nn0, Nn1, DATA2D.shape[0], DATA2D.shape[1])

        data_00: data_mod.DataWithAxes = data_raw.inav[0, :]
        assert data_00.shape == (Nn1, DATA2D.shape[0], DATA2D.shape[1])
        assert len(data_00.axes) == 3
        assert data_00.nav_indexes == (0, )
        assert data_00.get_axis_from_index(0)[0].label == 'nav1'

        data_01 = data_raw.inav[:, 2]
        assert data_01.shape == (Nn0, DATA2D.shape[0], DATA2D.shape[1])
        assert len(data_01.axes) == 3
        assert data_01.nav_indexes == (0, )
        assert data_01.get_axis_from_index(0)[0].label == 'nav0'

        data_1 = data_raw.inav[0, 2]
        assert data_1.shape == (DATA2D.shape[0], DATA2D.shape[1])
        assert len(data_1.axes) == 2
        assert data_1.nav_indexes == ()

        data_2: data_mod.DataWithAxes = data_raw.inav[0:3, 2:4]
        assert data_2.shape == (3, 2, DATA2D.shape[0], DATA2D.shape[1])
        assert data_2.get_axis_from_index(0)[0].size == 3
        assert data_2.get_axis_from_index(1)[0].size == 2

    def test_slice_ellipsis(self, init_data_uniform):
        data_raw = init_data_uniform
        assert data_raw.shape == (Nn0, Nn1, DATA2D.shape[0], DATA2D.shape[1])

        data_sliced = data_raw.inav[0, ...]
        assert data_sliced.nav_indexes == (0,)
        assert data_sliced.shape == (Nn1, DATA2D.shape[0], DATA2D.shape[1])

    def test_slice_miscellanous(self, init_data_uniform):
        data_raw = init_data_uniform
        assert data_raw.shape == (Nn0, Nn1, DATA2D.shape[0], DATA2D.shape[1])

        data_sliced = data_raw.inav[0:1, ...]
        assert data_sliced.shape == (Nn1, DATA2D.shape[0], DATA2D.shape[1])
        assert data_sliced.nav_indexes == (0,)



    def test_slice_signal(self, init_data_uniform):
        data_raw = init_data_uniform
        assert data_raw.shape == (Nn0, Nn1, DATA2D.shape[0], DATA2D.shape[1])

        data_00: data_mod.DataWithAxes = data_raw.isig[0, :]
        assert data_00.shape == (Nn0, Nn1, DATA2D.shape[1])
        assert len(data_00.axes) == 3
        assert data_00.nav_indexes == (0, 1)
        assert data_00.get_axis_from_index(2)[0].label == 'signal1'

        data_01 = data_raw.isig[:, 2]
        assert data_01.shape == (Nn0, Nn1, DATA2D.shape[0])
        assert len(data_01.axes) == 3
        assert data_01.nav_indexes == (0, 1)
        assert data_01.get_axis_from_index(2)[0].label == 'signal0'

        data_1 = data_raw.isig[0, 2]
        assert data_1.shape == (Nn0, Nn1)
        assert len(data_1.axes) == 2
        assert data_1.nav_indexes == (0, 1)

        data_2: data_mod.DataWithAxes = data_raw.isig[0:3, 2:4]
        assert data_2.shape == (Nn0, Nn1, 3, 2)
        assert data_2.get_axis_from_index(2)[0].size == 3
        assert data_2.get_axis_from_index(3)[0].size == 2


class TestSlicingSpread:
    def test_slice_navigation(self, init_data_spread):
        data, data_array, sig_axis, nav_axis_0, nav_axis_1, Nspread = init_data_spread

        data_0: data_mod.DataWithAxes = data.inav[3]
        assert data_0.shape == DATA1D.shape
        assert len(data_0.axes) == 1
        assert data_0.nav_indexes == ()
        assert data_0.axes[0].index == 0

        data_1: data_mod.DataWithAxes = data.inav[3:6]
        assert data_1.shape == (3, DATA1D.shape[0])
        assert len(data_1.axes) == 3
        assert data_1.nav_indexes == (0, )

    def test_slice_signal(self, init_data_spread):
        data, data_array, sig_axis, nav_axis_0, nav_axis_1, Nspread = init_data_spread

        data_0: data_mod.DataWithAxes = data.isig[3]
        assert data_0.shape == (Nspread, )
        assert len(data_0.axes) == 2
        assert data_0.nav_indexes == (0, )

        data_1: data_mod.DataWithAxes = data.isig[3:6]
        assert data_1.shape == (Nspread, 3)
        assert len(data_1.axes) == 3
        assert data_1.nav_indexes == (0, )


class TestDataSource:
    def test_data_from_plugins(self):
        Ndata = 2
        data = data_mod.DataFromPlugins('myData', data=[DATA2D for ind in range(Ndata)])
        assert isinstance(data, data_mod.DataWithAxes)
        assert data.source == data_mod.DataSource['raw']

    def test_data_raw(self):
        Ndata = 2
        data = data_mod.DataRaw('myData', data=[DATA2D for ind in range(Ndata)])
        assert isinstance(data, data_mod.DataWithAxes)
        assert data.source == data_mod.DataSource['raw']

    def test_data_calculated(self):
        Ndata = 2
        data = data_mod.DataCalculated('myData', data=[DATA2D for ind in range(Ndata)])
        assert isinstance(data, data_mod.DataWithAxes)
        assert data.source == data_mod.DataSource['calculated']

    def test_data_from_roi(self):
        Ndata = 2
        data = data_mod.DataFromRoi('myData', data=[DATA2D for ind in range(Ndata)])
        assert isinstance(data, data_mod.DataWithAxes)
        assert data.source == data_mod.DataSource['calculated']


class TestDataActuator:
    def test_init(self):
        Ndata = 2
        data = data_mod.DataActuator('myact')
        assert data.name == 'myact'
        assert data.data[0] == pytest.approx(0.)

        data = data_mod.DataActuator()
        assert data.name == 'actuator'
        assert data.dim == DataDim['Data0D']
        assert data.length == 1
        assert data.size == 1

        assert data.shape == (1, )
        assert data.data[0] == pytest.approx(0.)

    @pytest.mark.parametrize("data_number", [23, 0.25, -0.7, 1j*12])
    def test_quick_format(self, data_number):
        d = data_mod.DataActuator(data=data_number)
        assert d.name == 'actuator'
        assert d.data[0] == np.array([data_number])


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

    def test_getitem(self):
        dat0D = init_data(DATA0D, 2, name='my0DData', source='raw')
        dat1D_calculated = init_data(DATA1D, 2, name='my1DDatacalculated', source='calculated')
        dat1D_raw = init_data(DATA1D, 2, name='my1DDataraw', source='raw')

        data = data_mod.DataToExport(name='toexport', data=[dat0D, dat1D_calculated, dat1D_raw])

        assert isinstance(data[0], data_mod.DataWithAxes)

        assert data[0] == dat0D
        assert data[1] == dat1D_calculated
        assert data[2] == dat1D_raw

        index_slice = 1
        sliced_data = data[index_slice:]
        assert isinstance(sliced_data, data_mod.DataToExport)
        assert len(sliced_data) == len(data) - index_slice

        sliced_data = data[0:2]
        assert len(sliced_data) == 2
        assert sliced_data[0] == dat0D
        assert sliced_data[1] == dat1D_calculated

        sliced_data = data[0::2]
        assert len(sliced_data) == 2
        assert sliced_data[0] == dat0D
        assert sliced_data[1] == dat1D_raw

    def test_get_data_from_source(self):
        dat0D = init_data(DATA0D, 2, name='my0DData', source='raw')
        dat1D_calculated = init_data(DATA1D, 2, name='my1DDatacalculated', source='calculated')
        dat1D_raw = init_data(DATA1D, 2, name='my1DDataraw', source='raw')

        data = data_mod.DataToExport(name='toexport', data=[dat0D, dat1D_calculated, dat1D_raw])

        assert len(data.get_data_from_source('calculated')) == 1
        assert data.get_data_from_source('calculated').data == [dat1D_calculated]

        assert len(data.get_data_from_source('raw')) == 2
        assert data.get_data_from_source('raw').get_data_from_dim('Data0D').data == [dat0D]
        assert data.get_data_from_source('raw').get_data_from_dim('Data1D').data == [dat1D_raw]

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

    def test_get_data_from_name(self, ini_data_to_export):
        dat1, dat2, data = ini_data_to_export
        # without origin first
        assert data.get_data_from_name_origin('data2D') == dat1
        assert data.get_data_from_name_origin('data1D') == dat2
        dat3 = init_data(data=DATA2D, Ndata=1, name='data2Dbis')
        data.append(dat3)
        assert data.get_data_from_name_origin('data2Dbis') == dat3
        dat4 = init_data(data=DATA2D, Ndata=1, name='data2D')
        data.append(dat4)
        assert data.get_data_from_name_origin('data2D') == dat4
        assert dat1 not in data.data

    def test_get_data_from_name_origin(self, ini_data_to_export):
        dat1, dat2, data = ini_data_to_export
        # with origin
        assert data.get_data_from_name_origin('dataxxD', 'toexport') is None

        assert data.get_data_from_name_origin('data2D', 'toexport') == dat1
        assert data.get_data_from_name_origin('data2D', 'toexport2') is None
        assert data.get_data_from_name_origin('data1D', 'toexport') == dat2

    def test_get_data_from_full_names(self, ini_data_to_export):
        dat1, dat2, data = ini_data_to_export

        assert data.get_data_from_full_names(['toexport/data2D'])[0] == dat1
        assert data.get_data_from_full_names(['toexport/data1D'])[0] == dat2
        assert data.get_data_from_full_names(['toexport/data2D', 'toexport/data1D'])[0] == dat1
        assert data.get_data_from_full_names(['toexport/data2D', 'toexport/data1D'])[1] == dat2

    def test_index(self, ini_data_to_export):
        dat1, dat2, data = ini_data_to_export
        assert data.index(dat1) == 0
        assert data.index(dat1) == data.data.index(dat1)
        assert data.index(dat2) == data.data.index(dat2)

    def test_index_from_name_origin(self, ini_data_to_export):
        dat1, dat2, data = ini_data_to_export
        assert data.index_from_name_origin(dat1.name, dat1.origin) == data.index(dat1)
        assert data.index_from_name_origin(dat2.name, dat2.origin) == data.index(dat2)

    def test_pop(self, ini_data_to_export):
        dat1, dat2, data = ini_data_to_export
        assert len(data) == 2
        dat = data.pop(1)
        assert dat is dat2
        assert len(data) == 1
        with pytest.raises(ValueError):
            data.index(dat2)

    def test_get_names(self, ini_data_to_export):
        dat1, dat2, data = ini_data_to_export
        assert data.get_names() == ['data2D', 'data1D']
        assert data.get_names('Data1D') == ['data1D']
        assert data.get_names('Data2D') == ['data2D']

        dat3 = init_data(data=DATA2D, Ndata=1, name='data2Dbis')
        data.append(dat3)
        assert data.get_names('data2d') == ['data2D', 'data2Dbis']

    def test_math(self):
        dat1 = init_data(data=DATA2D, Ndata=2, name='data2D1')
        dat2 = init_data(data=0.2 * DATA2D, Ndata=2, name='data2D2')
        dat2bis = init_data(data=0.2 * DATA2D.reshape(DATA2D.shape[-1::-1]), Ndata=2, name='data2D2bis')
        dat3 = init_data(data=-0.7 * DATA2D, Ndata=2, name='data2D3')

        data1 = data_mod.DataToExport(name='toexport', data=[dat1, dat2])
        data2 = data_mod.DataToExport(name='toexport', data=[dat3, dat2])
        data3 = data_mod.DataToExport(name='toexport', data=[dat3, dat2bis])
        data4 = data_mod.DataToExport(name='toexport', data=[dat3, dat2, dat1])

        data_sum = data1 + data2
        data_diff = data1 - data2

        MUL_COEFF = 0.24
        DIV_COEFF = 12.7

        data_mul = data1 * MUL_COEFF
        data_div = data2 / DIV_COEFF

        assert data_sum[0] == dat1 + dat3
        assert data_sum[1] == dat2 + dat2

        assert data_diff[0] == dat1 - dat3
        assert data_diff[1] == dat2 - dat2

        with pytest.raises(ValueError):
            data1 + data3

        with pytest.raises(TypeError):
            data1 + data4

        assert data_mul[0] == dat1 * MUL_COEFF
        assert data_mul[1] == dat2 * MUL_COEFF

        assert data_div[0] == dat3 / DIV_COEFF
        assert data_div[1] == dat2 / DIV_COEFF

    def test_average(self):
        dat1 = init_data(data=DATA2D, Ndata=2, name='data2D1')
        dat2 = init_data(data=0.2 * DATA2D, Ndata=2, name='data2D2')
        dat3 = init_data(data=-0.7 * DATA2D, Ndata=2, name='data2D3')

        data1 = data_mod.DataToExport(name='toexport', data=[dat1, dat2])
        data2 = data_mod.DataToExport(name='toexport', data=[dat3, dat2])

        WEIGHT = 6

        data1 = data1.average(data2, WEIGHT)

        assert data1[0] == dat1.average(dat3, WEIGHT)
        assert data1[1] == dat2.average(dat2, WEIGHT)

    def test_merge(self):

        dat1 = init_data(data=DATA1D, Ndata=1, name='data1D1')
        dat2 = init_data(data=0.2 * DATA1D, Ndata=2, name='data1D2')
        dat3 = init_data(data=-0.7 * DATA1D, Ndata=3, name='data1D3')

        dte = data_mod.DataToExport('merging', data=[dat1, dat2, dat3])

        dwa = dte.merge_as_dwa('Data1D')

        assert len(dwa) == 6
        assert np.all(dwa[0] == pytest.approx(DATA1D))
        assert np.all(dwa[1] == pytest.approx(0.2*DATA1D))
        assert np.all(dwa[3] == pytest.approx(-0.7*DATA1D))
