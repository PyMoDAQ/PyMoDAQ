# -*- coding: utf-8 -*-
"""
Created the 21/11/2022

@author: Sebastien Weber
"""
import numpy as np
import pytest
from pathlib import Path

from pymodaq_data.h5modules import saving
from pymodaq_data.h5modules.data_saving import (
    DataLoader, AxisSaverLoader, DataSaverLoader, DataToExportSaver,
    DataEnlargeableSaver, DataToExportTimedSaver, SPECIAL_GROUP_NAMES, DataToExportExtendedSaver,
    DataToExportEnlargeableSaver, DataExtendedSaver, DataLoader, BkgSaver, squeeze)
from pymodaq_data.data import (Axis, DataWithAxes, DataSource, DataToExport, DataRaw,
                               DataDim, DataDistribution)


LABEL = 'A Label'
UNITS = 'um'
OFFSET = -20.4
SCALING = 0.22
SIZE = 20

DATA = OFFSET + SCALING * np.linspace(0, SIZE-1, SIZE)

DATA0D: np.ndarray = np.array([2.7])
DATA1D: np.ndarray = np.arange(0, 10)
DATA2D: np.ndarray = np.arange(0, 5*6).reshape((5, 6))
DATAND: np.ndarray = np.arange(0, 5 * 6 * 3).reshape((5, 6, 3))


def create_axis_array(size):
    return OFFSET + SCALING * np.linspace(0, size-1, size)


def init_axis(data=None, index=0):
    if data is None:
        data = DATA
    return Axis(label=LABEL, units=UNITS, data=data, index=index)


def init_data(data=None, Ndata=1, axes=(), name='myData') -> DataWithAxes:
    if data is None:
        data = DATA2D
    return DataWithAxes(name, DataSource(0), units='mm', data=[data for ind in range(Ndata)],
                                 axes=axes)


@pytest.fixture()
def init_data_to_export():
    Ndata = 2

    data2D = DataWithAxes(name='mydata2D', data=[DATA2D for _ in range(Ndata)],
                          labels=['mylabel1', 'mylabel2'],
                          source='raw',
                          dim='Data2D', distribution='uniform',
                          units='nm',
                          axes=[Axis(data=create_axis_array(DATA2D.shape[0]),
                                     label='myaxis0', units='myunits0',
                                     index=0),
                                Axis(data=create_axis_array(DATA2D.shape[1]),
                                     label='myaxis1', units='myunits1',
                                     index=1)],
                          errors=[np.random.random_sample(DATA2D.shape) for _ in range(Ndata)])

    data1D = DataWithAxes(name='mydata1D', data=[DATA1D for _ in range(Ndata)],
                          labels=['mylabel1', 'mylabel2'],
                          source='raw',
                          units='s',
                          dim='Data1D', distribution='uniform',
                          axes=[Axis(data=create_axis_array(DATA1D.shape[0]),
                                     label='myaxis0', units='myunits0',
                                     index=0)],
                          errors=None)

    data0D = DataWithAxes(name='mydata0D', data=[DATA0D for _ in range(Ndata)],
                          labels=['mylabel1', 'mylabel2'],
                          source='raw', dim='Data0D', distribution='uniform',
                          units='um',
                          errors=[np.random.random_sample(DATA0D.shape) for _ in range(Ndata)])

    data0Dbis = DataWithAxes(name='mydata0Dbis', data=[DATA0D for _ in range(Ndata)],
                             labels=['mylabel1bis', 'mylabel2bis'], source='raw', dim='Data0D',
                             units='um',
                             distribution='uniform')

    data_to_export = DataToExport(name='mybigdata', data=[data2D, data0D, data1D, data0Dbis])
    return data_to_export

@pytest.fixture()
def create_h5_with_data_to_export(h5saver_lowlevel, init_data_to_export):
    dte = init_data_to_export
    data_saver = DataToExportSaver(h5saver_lowlevel)

    det_group = h5saver_lowlevel.get_set_group(h5saver_lowlevel.raw_group, 'MyDet')
    data_saver.add_data(det_group, dte)
    return h5saver_lowlevel


class TestAxisSaverLoader:

    def test_init(self, h5saver_lowlevel):
        h5saver = h5saver_lowlevel
        axis_saver = AxisSaverLoader(h5saver)
        assert axis_saver.data_type.name == 'axis'

    def test_add_axis(self, h5saver_lowlevel):
        h5saver = h5saver_lowlevel
        axis_saver = AxisSaverLoader(h5saver)
        SIZE = 10
        OFFSET = -5.
        SCALING = 0.2
        INDEX = 5
        LABEL = 'myaxis'
        UNITS = 'ms'
        axis = Axis(label=LABEL, units=UNITS,
                    data=OFFSET + SCALING * np.linspace(0, SIZE-1, SIZE), index=INDEX)

        axis_node = axis_saver.add_axis(h5saver.raw_group, axis)

        attrs = ['label', 'units', 'offset', 'scaling', 'index']
        attrs_values = [LABEL, UNITS, OFFSET, SCALING, INDEX]
        for ind, attr in enumerate(attrs):
            assert attr in axis_node.attrs
            if isinstance(attrs_values[ind], float):
                assert axis_node.attrs[attr] == pytest.approx(attrs_values[ind])
            else:
                assert axis_node.attrs[attr] == attrs_values[ind]
        assert axis_node.read() == pytest.approx(axis.get_data())

    def test_load_axis(self, h5saver_lowlevel):
        h5saver = h5saver_lowlevel
        axis_saver = AxisSaverLoader(h5saver)
        SIZE = 10
        OFFSET = -5.
        SCALING = 0.2
        INDEX = 5
        LABEL = 'myaxis'
        UNITS = 'ms'
        axis = Axis(label=LABEL, units=UNITS,
                    data=OFFSET + SCALING * np.linspace(0, SIZE - 1, SIZE), index=INDEX)

        axis_node = axis_saver.add_axis(h5saver.raw_group, axis)

        axis_back = axis_saver.load_axis(axis_node)
        assert isinstance(axis_back, Axis)
        assert axis_back == axis

    def test_add_multiple_axis(self, h5saver_lowlevel):
        h5saver = h5saver_lowlevel
        axis_saver = AxisSaverLoader(h5saver)
        SIZE = 10
        OFFSET = -5.
        SCALING = 0.2
        LABEL = 'myaxis'
        UNITS = 'myunits'
        axes_ini = []
        for ind in range(3):
            axes_ini.append(Axis(label=f'LABEL{ind}', units=f'UNITS{ind}',
                                 data=OFFSET + SCALING * np.linspace(0, SIZE-1, SIZE),
                                 index=ind))
            axis_node = axis_saver.add_axis(h5saver.raw_group, axes_ini[ind])
            assert axis_node.name == axis_saver._format_node_name(ind)
            assert axis_node.attrs['label'] == f'LABEL{ind}'
            assert axis_node.attrs['index'] == ind
            assert axis_node.attrs['data_type'] == axis_saver.data_type

        axes_out = axis_saver.get_axes(h5saver.raw_group)
        for axis_ini, axis_out in zip(axes_ini, axes_out):
            assert axis_ini == axis_out

        for axis_ini, axis_out in zip(axes_ini, axis_saver.get_axes(axis_node)):
            assert axis_ini == axis_out


class TestDataSaverLoader:
    def test_init(self, h5saver_lowlevel):
        h5saver = h5saver_lowlevel
        data_saver = DataSaverLoader(h5saver)
        assert data_saver.data_type.name == 'data'

    def test_add_data(self, h5saver_lowlevel):
        h5saver = h5saver_lowlevel
        data_saver = DataSaverLoader(h5saver)
        Ndata = 2

        data = DataWithAxes(name='mydata', data=[DATA2D for _ in range(Ndata)], labels=['mylabel1', 'mylabel2'],
                            source='raw',
                            dim='Data2D', distribution='uniform',
                            axes=[Axis(data=create_axis_array(DATA2D.shape[0]), label='myaxis0', units='myunits0',
                                       index=0),
                                  Axis(data=create_axis_array(DATA2D.shape[1]), label='myaxis1', units='myunits1',
                                       index=1)])

        data_saver.add_data(h5saver.raw_group, data)
        assert len(data_saver.get_axes(h5saver.raw_group)) == Ndata
        for axis_in, axis_out in zip(data.axes, data_saver.get_axes(h5saver.raw_group)):
            assert axis_in == axis_out

    def test_add_data_with_errors(self, h5saver_lowlevel):
        h5saver = h5saver_lowlevel
        data_saver = DataSaverLoader(h5saver)
        Ndata = 2

        errors = [np.random.random_sample(DATA2D.shape) for _ in range(Ndata)]

        data = DataWithAxes(name='mydata', data=[DATA2D for _ in range(Ndata)],
                            labels=['mylabel1', 'mylabel2'],
                            source='raw',
                            units='mm',
                            dim='Data2D', distribution='uniform',
                            axes=[Axis(data=create_axis_array(DATA2D.shape[0]),
                                       label='myaxis0', units='myunits0',
                                       index=0),
                                  Axis(data=create_axis_array(DATA2D.shape[1]),
                                       label='myaxis1', units='myunits1',
                                       index=1)],
                            errors=errors)

        data_saver.add_data(h5saver.raw_group, data)
        assert len(data_saver.get_axes(h5saver.raw_group)) == Ndata
        for axis_in, axis_out in zip(data.axes, data_saver.get_axes(h5saver.raw_group)):
            assert axis_in == axis_out

        assert np.all(errors[0] == data_saver._error_saver.get_node_from_index('/RawData', 0).read())
        assert np.all(errors[1] == data_saver._error_saver.get_node_from_index('/RawData', 1).read())

    def test_load_data(self, h5saver_lowlevel):
        h5saver = h5saver_lowlevel
        data_saver = DataSaverLoader(h5saver)
        Ndata = 2
        errors = [np.random.random_sample(DATA1D.shape) for _ in range(Ndata)]

        data = DataWithAxes(name='mydata', data=[DATA1D for _ in range(Ndata)],
                            labels=['mylabel1', 'mylabel2'],
                            source='raw',
                            units='mm',
                            dim='Data2D', distribution='uniform',
                            axes=[Axis(data=create_axis_array(DATA1D.shape[0]),
                                       label='myaxis0', units='mm',
                                       index=0),
                                 ],
                            errors=errors)
        data_saver.add_data(h5saver.raw_group, data)

        loaded_data = data_saver.load_data(h5saver.get_node('/RawData/Data00'), load_all=True)
        assert len(loaded_data) == 2
        assert loaded_data == data
        assert loaded_data.labels == data.labels
        for ind in range(Ndata):
            assert np.all(loaded_data.errors[ind] == errors[ind])

        loaded_data = data_saver.load_data(h5saver.get_node('/RawData/Data01'), load_all=True)
        assert len(loaded_data) == 2
        assert loaded_data == data
        assert loaded_data.labels == data.labels
        for ind in range(Ndata):
            assert np.all(loaded_data.errors[ind] == errors[ind])

        for INDEX in range(2):
            loaded_data = data_saver.load_data(h5saver.get_node(f'/RawData/Data0{INDEX}'), load_all=False)
            assert len(loaded_data) == 1
            assert loaded_data.labels == [data.labels[INDEX]]
            assert np.allclose(loaded_data.data, data[INDEX])
            assert len(loaded_data.errors) == 1
            assert np.allclose(loaded_data.errors[0], errors[INDEX])

    def test_load_with_bkg(self, h5saver_lowlevel):
        h5saver = h5saver_lowlevel
        data_saver = DataSaverLoader(h5saver)
        bkgSaver = BkgSaver(h5saver)

        axes = [Axis(data=create_axis_array(DATA2D.shape[0]), label='myaxis0', units='mm',
                     index=0),
                Axis(data=create_axis_array(DATA2D.shape[1]), label='myaxis1', units='um',
                     index=1)]

        Ndata = 2
        data = DataWithAxes(name='mydata', data=[DATA2D for _ in range(Ndata)], labels=['mylabel1', 'mylabel2'],
                            source='raw',
                            dim='Data2D', distribution='uniform', axes=axes)
        data_saver.add_data(h5saver.raw_group, data)
        bkgSaver.add_data('/RawData', data)

        loaded_data = data_saver.load_data(h5saver.get_node('/RawData/Data01'), load_all=True, with_bkg=True)
        assert len(loaded_data) == 2
        assert loaded_data.labels == data.labels

        for dat in loaded_data:
            assert np.allclose(dat, np.zeros(dat.shape))

        assert loaded_data == data-data


    def test_extra_attributes_and_timestamping(self, h5saver_lowlevel):
        h5saver = h5saver_lowlevel
        data_saver = DataSaverLoader(h5saver)
        Ndata = 2

        data = DataWithAxes(name='mydata', data=[DATA2D for _ in range(Ndata)],
                            labels=['mylabel1', 'mylabel2'],
                            source='raw',
                            dim='Data2D', distribution='uniform',
                            axes=[Axis(data=create_axis_array(DATA2D.shape[0]),
                                       label='myaxis0', units='s',
                                       index=0),
                                  Axis(data=create_axis_array(DATA2D.shape[1]),
                                       label='myaxis1', units='ms',
                                       index=1)],
                            another_attribute='another_attribute',
                            another_other_attribute=123)

        data_saver.add_data(h5saver.raw_group, data)
        loaded_data = data_saver.load_data(h5saver.get_node('/RawData/Data01'), load_all=True, with_bkg=True)
        assert loaded_data == data
        node = h5saver.get_node('/RawData/Data01')
        assert 'another_attribute' in node.attrs
        assert node.attrs['another_attribute'] == 'another_attribute'
        assert 'another_other_attribute' in node.attrs
        assert node.attrs['another_other_attribute'] == 123

        assert loaded_data.another_attribute == 'another_attribute'
        assert 'another_other_attribute' in node.attrs
        assert loaded_data.another_other_attribute == 123
        assert loaded_data.timestamp == data.timestamp


class TestBkgSaver:
    def test_load_data(self, h5saver_lowlevel):
        h5saver = h5saver_lowlevel
        bkgSaver = BkgSaver(h5saver)

        axes = [Axis(data=create_axis_array(DATA2D.shape[0]), label='myaxis0', units='ms',
                     index=0),
                Axis(data=create_axis_array(DATA2D.shape[1]), label='myaxis1', units='s',
                     index=1)]

        data_bkg = init_data(DATA2D, axes=axes, name='mykbg')
        bkgSaver.add_data(h5saver.raw_group, data_bkg)

        data_bkg_loaded = bkgSaver.load_data('/RawData/Bkg00')
        assert data_bkg_loaded == data_bkg


class TestDataEnlargeableSaver:
    def test_init(self, h5saver_lowlevel):
        h5saver = h5saver_lowlevel
        data_saver = DataEnlargeableSaver(h5saver)
        assert data_saver.data_type.value == 'EnlData'
        assert data_saver.data_type.name == 'data_enlargeable'

    @pytest.mark.parametrize('Nenl', [1, 2, 3])
    @pytest.mark.parametrize('data_array', [DATA0D, DATA1D, DATA2D])
    def test_add_data(self, h5saver_lowlevel, data_array, Nenl):
        h5saver = h5saver_lowlevel

        Ndata = 2

        axis_values = tuple(np.random.randn(Nenl))
        data_saver = DataEnlargeableSaver(h5saver,
                                          enl_axis_names=['ax' for _ in range(Nenl)],
                                          enl_axis_units=['units' for _ in range(Nenl)])

        data = DataWithAxes(name='mydata', data=[data_array for _ in range(Ndata)],
                            labels=['mylabel1', 'mylabel2'],
                            source='raw', distribution='uniform')
        data.create_missing_axes()

        data_saver.add_data(h5saver.raw_group, data, axis_values=axis_values)

        data_node = h5saver.get_node('/RawData/EnlData00')

        ESHAPE = [1]
        ESHAPE += list(data_array.shape)
        assert data_node.attrs['shape'] == tuple(ESHAPE)
        data_saver.add_data(h5saver.raw_group, data, axis_values=axis_values)
        ESHAPE = [2]
        ESHAPE += list(data_array.shape)
        assert data_node.attrs['shape'] == tuple(ESHAPE)

        dwa_back = data_saver.load_data('/RawData/EnlData00')
        assert dwa_back.inav[0] == data.pop(0)
        assert len(dwa_back.get_nav_axes()) == Nenl
        if Nenl > 0:
            assert len(dwa_back.get_nav_axes()[0]) == 2

    def test_add_data_ndviewer_0D(self, h5saver_lowlevel):
        h5saver = h5saver_lowlevel
        Npts = 11
        Ndata = 1
        data_array_0D = np.linspace(0, 100, Npts)
        axis_array = np.linspace(0, 1, Npts)
        axis_values = Axis('enlaxis', units='s', data=axis_array)
        Nenl=1
        data_saver = DataEnlargeableSaver(h5saver)

        data = DataRaw(name='mynddata', data=[data_array_0D for _ in range(Ndata)],
                       labels=['mylabel1'],
                       nav_indexes=(0,),
                       axes=[axis_values])

        data_saver.add_data(h5saver.raw_group, data)

        dwa_back = data_saver.load_data('/RawData/EnlData00')
        for ind in range(len(data_array_0D)):
            assert dwa_back.inav[ind].data[0][0] == data_array_0D[ind]
        assert dwa_back.get_axis_from_index(dwa_back.nav_indexes[0])[0] == axis_values


        data_saver.add_data(h5saver.raw_group, data)
        dwa_back = data_saver.load_data('/RawData/EnlData00')

        assert len(dwa_back.axes[0]) == 2 * len(axis_array)
        assert dwa_back.size == 2 * len(axis_array)


    def test_add_data_ndviewer_1D(self, h5saver_lowlevel):
        h5saver = h5saver_lowlevel
        Npts_nav = 11
        Npts_sig = 21
        Ndata = 1
        data_array_1D_1D = np.arange(Npts_sig*Npts_nav).reshape((Npts_nav, Npts_sig))
        axis_array_sig = np.linspace(0, 100, Npts_sig)
        axis_array_nav = np.linspace(0, 1, Npts_nav)
        axis_nav = Axis('enlaxis', units='s', data=axis_array_nav, index=0)
        axis_sig = Axis('sigaxis', units='m', data=axis_array_sig, index=1)

        data_saver = DataEnlargeableSaver(h5saver)

        data = DataRaw(name='mynddata', data=[data_array_1D_1D for _ in range(Ndata)],
                       labels=['mylabel1'],
                       nav_indexes=(0,),
                       axes=[axis_nav, axis_sig])

        data_saver.add_data(h5saver.raw_group, data)

        dwa_back = data_saver.load_data('/RawData/EnlData00')
        for ind in range(data_array_1D_1D.shape[0]):
            assert np.allclose(dwa_back.inav[ind].data[0], data_array_1D_1D[ind])
        assert dwa_back.get_axis_from_index(0)[0] == axis_nav
        assert dwa_back.get_axis_from_index(1)[0] == axis_sig

        data_saver.add_data(h5saver.raw_group, data)
        dwa_back = data_saver.load_data('/RawData/EnlData00')

        assert len(dwa_back.get_axis_from_index(0)[0]) == 2 * len(axis_nav)
        assert dwa_back.size == 2 * len(axis_nav) * Npts_sig


class TestDataExtendedSaver:
    def test_init(self, h5saver_lowlevel):
        h5saver = h5saver_lowlevel
        EXT_SHAPE = (5, 10)
        data_saver = DataExtendedSaver(h5saver, EXT_SHAPE)
        assert data_saver.data_type.value == 'Data'
        assert data_saver.data_type.name == 'data'
        assert data_saver.extended_shape == EXT_SHAPE

    def test_add_data(self, h5saver_lowlevel):
        h5saver = h5saver_lowlevel

        EXT_SHAPE = (5, 10)
        data_saver = DataExtendedSaver(h5saver, EXT_SHAPE)

        Ndata = 2

        data = DataWithAxes(name='mydata', data=[DATA2D for _ in range(Ndata)],
                            labels=['mylabel1', 'mylabel2'],
                            source='raw',
                            dim='Data2D', distribution='uniform',
                            axes=[Axis(data=create_axis_array(DATA2D.shape[0]), label='myaxis0',
                                       units='ms',
                                       index=0),
                                  Axis(data=create_axis_array(DATA2D.shape[1]), label='myaxis1',
                                       units='s',
                                       index=1)])
        data_ext_shape = list(EXT_SHAPE)
        data_ext_shape.extend(data.shape)

        INDEXES = [4, 3]
        data_saver.add_data(h5saver.raw_group, data, indexes=INDEXES)
        assert len(data_saver.get_axes(h5saver.raw_group)) == Ndata
        for ind in range(len(data)):
            data_node = h5saver.get_node(f'/RawData/Data0{ind}')

            assert data_node.attrs['shape'] == tuple(data_ext_shape)
            assert np.all(data_node[tuple(INDEXES)] == pytest.approx(data[ind]))


    @pytest.mark.parametrize('fill_value,checker', [
        (0.0, lambda a: np.all(a == 0.0)),
        (-1.0, lambda a: np.all(a == -1.0)),
        (np.nan, lambda a: np.all(np.isnan(a))),
    ])
    def test_fill_value(self, h5saver_lowlevel, fill_value, checker):
        """Unwritten scan positions contain fill_value; written position has real data."""
        h5saver = h5saver_lowlevel
        EXT_SHAPE = (5,)
        data_saver = DataExtendedSaver(h5saver, EXT_SHAPE, fill_value=fill_value)

        # Use float64 data so NaN can be stored (integer arrays silently cast NaN to 0)
        data_float = DATA1D.astype(np.float64)
        data = DataWithAxes(name='mydata', data=[data_float],
                            source='raw', dim='Data1D', distribution='uniform',
                            axes=[Axis(data=create_axis_array(data_float.shape[0]),
                                       label='myaxis0', units='ms', index=0)])

        WRITE_INDEX = [2]
        data_saver.add_data(h5saver.raw_group, data, indexes=WRITE_INDEX)

        arr = h5saver.get_node('/RawData/Data00').read()
        assert arr.shape == (EXT_SHAPE[0], data_float.shape[0])
        assert np.allclose(arr[WRITE_INDEX[0]], data_float)
        # All other scan positions should contain fill_value
        other = np.delete(arr, WRITE_INDEX[0], axis=0)
        assert checker(other)

    def test_fill_value_defaults_to_h5saver(self, h5saver_lowlevel):
        """When no fill_value given, DataExtendedSaver inherits h5saver.fill_value."""
        h5saver = h5saver_lowlevel
        h5saver.fill_value = np.nan
        data_saver = DataExtendedSaver(h5saver, (3,))

        # Use float64 data so NaN can be stored
        data_float = DATA1D.astype(np.float64)
        data = DataWithAxes(name='mydata', data=[data_float],
                            source='raw', dim='Data1D', distribution='uniform',
                            axes=[Axis(data=create_axis_array(data_float.shape[0]),
                                       label='ax0', units='ms', index=0)])
        data_saver.add_data(h5saver.raw_group, data, indexes=[0])

        arr = h5saver.get_node('/RawData/Data00').read()
        assert np.all(np.isnan(arr[1]))
        assert np.all(np.isnan(arr[2]))


class TestDataToExportSaver:
    def test_save(self, create_h5_with_data_to_export):
        h5saver = create_h5_with_data_to_export


class TestDataToExportEnlargeableSaver:

    def test_save(self, h5saver_lowlevel, init_data_to_export):
        h5saver = h5saver_lowlevel
        data_to_export = init_data_to_export
        det_group = h5saver.get_set_group(h5saver.raw_group, 'MyDet')

        data_saver = DataToExportEnlargeableSaver(h5saver)

        Nadd_data = 2
        for ind in range(Nadd_data):
            data_saver.add_data(det_group, data_to_export, axis_value=27.)

        for node in h5saver.walk_nodes('/'):
            if 'shape' in node.attrs and node.name != 'Logger' and 'data' in node.attrs['data_type']:
                assert node.attrs['shape'][0] == Nadd_data

        data_saver.add_data(det_group, data_to_export, axis_value=72.)
        for node in h5saver.walk_nodes('/'):
            if 'shape' in node.attrs and node.name != 'Logger' and 'data' in node.attrs['data_type']:
                assert node.attrs['shape'][0] == Nadd_data + 1

    @pytest.mark.parametrize('data_array', [DATA0D, DATA1D, DATA2D])
    @pytest.mark.parametrize('Nenl', [1, 2, 3])
    def test_spread_data(self, h5saver_lowlevel, Nenl, data_array):
        h5saver = h5saver_lowlevel

        dte_saver = DataToExportEnlargeableSaver(h5saver,
                                                 enl_axis_names=['ax' for _ in range(Nenl)],
                                                 enl_axis_units=['units' for _ in range(Nenl)],
                                                 )
        dte_loader = DataLoader(h5saver)

        axis_values = list(np.random.randn(Nenl))

        dwa = DataRaw('dwa', data=[data_array],
                      distribution=DataDistribution.spread)
        dwa.create_missing_axes()

        dte = DataToExport('dte', data=[dwa])
        dte_saver.add_data(h5saver.raw_group, data=dte, axis_values=axis_values)

        data_loaded = dte_loader.load_data(
            f'/RawData/{DataDim.from_data_array(data_array).name}/CH00/EnlData00')
        assert data_loaded.inav[0] == dwa


class TestDataToExportTimedSaver:
    def test_save(self, h5saver_lowlevel, init_data_to_export):
        h5saver = h5saver_lowlevel
        data_to_export = init_data_to_export
        det_group = h5saver.get_set_group(h5saver.raw_group, 'MyDet')

        data_saver = DataToExportTimedSaver(h5saver)
        Nadd_data = 2
        for ind in range(Nadd_data):
            data_saver.add_data(det_group, data_to_export)

        for node in h5saver.walk_nodes('/'):
            if 'shape' in node.attrs and node.name != 'Logger' and 'data' in node.attrs['data_type']:
                assert node.attrs['shape'][0] == Nadd_data

        data_saver.add_data(det_group, data_to_export)
        for node in h5saver.walk_nodes('/'):
            if 'shape' in node.attrs and node.name != 'Logger' and 'data' in node.attrs['data_type']:
                assert node.attrs['shape'][0] == Nadd_data + 1


class TestDataToExportExtendedSaver:
    def test_save(self, h5saver_lowlevel, init_data_to_export):
        h5saver = h5saver_lowlevel
        data_to_export = init_data_to_export
        det_group = h5saver.get_set_group(h5saver.raw_group, 'MyDet')

        EXT_SHAPE = (5, 10)
        nav_axes = []
        nav_axes.append(Axis('navaxis0', '', data=np.linspace(0, EXT_SHAPE[0]-1, EXT_SHAPE[0]), index=0))
        nav_axes.append(Axis('navaxis1', '', data=np.linspace(0, EXT_SHAPE[1] - 1, EXT_SHAPE[1]), index=1))

        data_saver = DataToExportExtendedSaver(h5saver, extended_shape=EXT_SHAPE)

        INDEXES = [4, 3]
        data_saver.add_nav_axes(det_group, nav_axes)
        data_saver.add_data(det_group, data_to_export, INDEXES)


    def test_fill_value_nan_unwritten_positions(self, h5saver_lowlevel):
        """NaN fill: positions not yet written contain NaN; written position has real data."""
        h5saver = h5saver_lowlevel
        det_group = h5saver.get_set_group(h5saver.raw_group, 'MyDet')

        # Use float64 data so NaN can be stored (integer arrays silently cast NaN to 0)
        data_float = DATA1D.astype(np.float64)
        data_to_export = DataToExport(name='mydata', data=[
            DataWithAxes(name='mydata1D', data=[data_float],
                         source='raw', dim='Data1D', distribution='uniform',
                         axes=[Axis(data=create_axis_array(data_float.shape[0]),
                                    label='ax0', units='ms', index=0)]),
        ])

        EXT_SHAPE = (4, 3)
        data_saver = DataToExportExtendedSaver(h5saver, extended_shape=EXT_SHAPE,
                                               fill_value=np.nan)
        INDEXES = [1, 2]
        data_saver.add_data(det_group, data_to_export, INDEXES)

        for node in h5saver.walk_nodes('/RawData/MyDet'):
            if 'data_type' not in node.attrs:
                continue
            if node.attrs['data_type'] not in ('data', 'Data'):
                continue
            arr = node.read()
            # written position should be finite
            assert np.all(np.isfinite(arr[tuple(INDEXES)]))
            # a different position should be NaN
            other_idx = (0, 0)
            assert np.all(np.isnan(arr[other_idx]))


class TestDataLoader:
    def test_load_normal_data(self, create_h5_with_data_to_export):
        h5saver = create_h5_with_data_to_export
        data_loader = DataLoader(create_h5_with_data_to_export)

        data_loaded = data_loader.load_data(h5saver.get_node('/RawData/MyDet/Data2D/CH00/Data00'))
        assert len(data_loaded) == 1
        for ind in range(len(data_loaded)):
            assert np.all(data_loaded[ind] == pytest.approx(DATA2D))

    def test_load_one_node(self, create_h5_with_data_to_export):
        h5saver = create_h5_with_data_to_export
        data_loader = DataLoader(h5saver)

        data_loaded = data_loader.load_data(h5saver.get_node('/RawData/MyDet/Data2D/CH00/Data00'))
        assert len(data_loaded) == 1

        data_loaded = data_loader.load_data(h5saver.get_node('/RawData/MyDet/Data2D/CH00/Data01'), load_all=True)
        assert len(data_loaded) == 2

    def test_load_normal_data_with_bkg(self, h5saver_lowlevel, init_data_to_export):
        h5saver = h5saver_lowlevel
        data_to_export = init_data_to_export
        data_loader = DataLoader(h5saver)

        data_saver = DataToExportSaver(h5saver)
        det_group = h5saver.get_set_group(h5saver.raw_group, 'MyDet')

        data_saver.add_data(det_group, data_to_export)
        data_saver.add_bkg(det_group, data_to_export)

        data_loaded = data_loader.load_data(h5saver.get_node('/RawData/MyDet/Data2D/CH00/Data00'), with_bkg=True)
        for ind in range(len(data_loaded)):
            assert np.all(data_loaded[ind] == pytest.approx(0 * DATA2D))

    def test_load_enlargeable_data(self, h5saver_lowlevel, init_data_to_export):
        h5saver = h5saver_lowlevel
        data_to_export = init_data_to_export
        data_loader = DataLoader(h5saver)

        data_saver = DataToExportTimedSaver(h5saver)
        det_group = h5saver.get_set_group(h5saver.raw_group, 'MyDet')

        Nadd_data = 3
        for ind in range(Nadd_data):
            data_saver.add_data(det_group, data_to_export)

        assert data_loader.get_nav_group('/RawData/MyDet/Data2D/CH00/EnlData00') == \
               h5saver.get_node(f'/RawData/MyDet/{SPECIAL_GROUP_NAMES["nav_axes"]}')
        nav_axis_node = h5saver.get_node('/RawData/MyDet/NavAxes/Axis00')
        assert nav_axis_node.attrs['shape'] == (Nadd_data,)
        assert nav_axis_node.attrs['index'] == 0

        data_loaded = data_loader.load_data('/RawData/MyDet/Data2D/CH00/EnlData00')
        for ind in range(len(data_loaded)):
            assert np.all(data_loaded[ind][0] == pytest.approx(DATA2D))
            assert np.all(data_loaded[ind][1] == pytest.approx(DATA2D))

    def test_load_all(self, h5saver_lowlevel, init_data_to_export):
        h5saver = h5saver_lowlevel
        data_to_export = init_data_to_export
        data_loader = DataLoader(h5saver)

        data_saver = DataToExportSaver(h5saver)
        det_group = h5saver.get_set_group(h5saver.raw_group, 'MyDet')

        data_saver.add_data(det_group, data_to_export)
        data_saver.add_bkg(det_group, data_to_export)
        data_all = DataToExport('All')
        data_loader.load_all('/RawData', data_all, with_bkg=True)
        assert len(data_all) == 4

        for dwa in data_all:
            assert len(dwa) == 2
            for data_array in dwa:
                assert np.allclose(data_array, np.zeros(data_array.shape))

    def test_load_data_from_axis_node(self, h5saver_lowlevel):
        """This is what happens in the h5browser to display axes in the viewers"""
        h5saver = h5saver_lowlevel
        data_loader = DataLoader(h5saver)

        axis_saver = AxisSaverLoader(h5saver)
        SIZE = 10
        OFFSET = -5.
        SCALING = 0.2
        INDEX = 5
        LABEL = 'myaxis'
        UNITS = 'ms'
        axis = Axis(label=LABEL, units=UNITS,
                    data=OFFSET + SCALING * np.linspace(0, SIZE - 1, SIZE), index=INDEX)

        axis_node = axis_saver.add_axis(h5saver.raw_group, axis)

        dwa = data_loader.load_data(axis_node.path)

        assert np.allclose(dwa[0], axis.get_data())
        assert dwa.name == LABEL
        #missing handling units?

        assert dwa.axes[0].label == LABEL  # should not be that as the retrieved axis label of an
        # axis node from this type of loading should be 'index'
        assert dwa.axes[0].units == UNITS  # should not be that as the retrieved axis units of an
        # axis node from this type of loading should be ''

    def test_load_data_from_name_origin(self, h5saver_lowlevel, init_data_to_export):
        h5saver = h5saver_lowlevel
        dte = init_data_to_export

        with DataToExportSaver(h5saver) as data_saver:
            det_group = h5saver.get_set_group(h5saver.raw_group, 'MyDet')
            data_saver.add_data(det_group, dte)

            with DataLoader(h5saver) as data_loader:
                for dwa in dte:
                    dwa_loaded = data_loader.load_data_from_name_origin(
                        name=dwa.name, origin=dwa.origin,
                    )
                    assert dwa_loaded == dwa

                with pytest.raises(NameError):
                    dwa_loaded = data_loader.load_data_from_name_origin(
                        name='aunknown name', origin='and_origin',
                    )