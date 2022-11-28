# -*- coding: utf-8 -*-
"""
Created the 21/11/2022

@author: Sebastien Weber
"""
import numpy as np
import pytest

from pymodaq.utils.h5modules import saving
from pymodaq.utils.h5modules.data_saving import DataSaver, AxisSaverLoader, DataSaverLoader, DataToExportSaverLoader, \
    DataEnlargeableSaverLoader, DataToExportEnlargeableLoaderSaver
from pymodaq.utils.data import Axis, DataWithAxes, DataSource, DataToExport


@pytest.fixture()
def get_h5saver(tmp_path):
    h5saver = saving.H5SaverLowLevel()
    addhoc_file_path = tmp_path.joinpath('h5file.h5')
    h5saver.init_file(file_name=addhoc_file_path, file_type=saving.FileType['detector'])

    yield h5saver
    h5saver.close_file()


LABEL = 'A Label'
UNITS = 'units'
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


def init_data(data=None, Ndata=1, axes=[], name='myData') -> DataWithAxes:
    if data is None:
        data = DATA2D
    return DataWithAxes(name, DataSource(0), data=[data for ind in range(Ndata)],
                                 axes=axes)


class TestAxisSaverLoader:

    def test_init(self, get_h5saver):
        h5saver = get_h5saver
        axis_saver = AxisSaverLoader(h5saver)
        assert axis_saver.data_type.name == 'axis'

    def test_add_axis(self, get_h5saver):
        h5saver = get_h5saver
        axis_saver = AxisSaverLoader(h5saver)
        SIZE = 10
        OFFSET = -5.
        SCALING = 0.2
        INDEX = 5
        LABEL = 'myaxis'
        UNITS = 'myunits'
        axis = Axis(label=LABEL, units=UNITS, data=OFFSET + SCALING * np.linspace(0, SIZE-1, SIZE), index=INDEX)

        axis_node = axis_saver.add_axis(h5saver.raw_group, axis)

        attrs = ['label', 'units', 'offset', 'scaling', 'index']
        attrs_values = [LABEL, UNITS, OFFSET, SCALING, INDEX]
        for ind, attr in enumerate(attrs):
            assert attr in axis_node.attrs
            if isinstance(attrs_values[ind], float):
                assert axis_node.attrs[attr] == pytest.approx(attrs_values[ind])
            else:
                assert axis_node.attrs[attr] == attrs_values[ind]
        assert axis_node.read() == pytest.approx(axis.data)

    def test_load_axis(self, get_h5saver):
        h5saver = get_h5saver
        axis_saver = AxisSaverLoader(h5saver)
        SIZE = 10
        OFFSET = -5.
        SCALING = 0.2
        INDEX = 5
        LABEL = 'myaxis'
        UNITS = 'myunits'
        axis = Axis(label=LABEL, units=UNITS, data=OFFSET + SCALING * np.linspace(0, SIZE - 1, SIZE), index=INDEX)

        axis_node = axis_saver.add_axis(h5saver.raw_group, axis)

        axis_back = axis_saver.load_axis(axis_node)
        assert isinstance(axis_back, Axis)
        assert axis_back == axis

    def test_add_multiple_axis(self, get_h5saver):
        h5saver = get_h5saver
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
            axis_node = axis_saver.add_axis(h5saver.raw_group, axes_ini[-1])
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
    def test_init(self, get_h5saver):
        h5saver = get_h5saver
        data_saver = DataSaverLoader(h5saver)
        assert data_saver.data_type.name == 'data'

    def test_add_data(self, get_h5saver):
        h5saver = get_h5saver
        data_saver = DataSaverLoader(h5saver)
        Ndata = 2

        data = DataWithAxes(name='mydata', data=[DATA2D for _ in range(Ndata)], labels=['mylabel1', 'mylabel2'],
                            source='raw',
                            dim='Data2D', distribution='uniform',
                            axes=[Axis(data=create_axis_array(DATA2D.shape[0]), label='myaxis0', units='myunits0',
                                       index=0),
                                  Axis(data=create_axis_array(DATA2D.shape[1]), label='myaxis1', units='myunits1',
                                       index=1),])

        data_saver.add_data(h5saver.raw_group, data)
        assert len(data_saver.get_axes(h5saver.raw_group)) == Ndata
        for axis_in, axis_out in zip(data.axes, data_saver.get_axes(h5saver.raw_group)):
            assert axis_in == axis_out

        assert data_saver.load_data(h5saver.get_node('/RawData/Data00')) == data
        assert data_saver.load_data(h5saver.raw_group) == data


class TestDataEnlargeableSaverLoader:
    def test_init(self, get_h5saver):
        h5saver = get_h5saver
        data_saver = DataEnlargeableSaverLoader(h5saver)
        assert data_saver.data_type.value == 'EnlData'
        assert data_saver.data_type.name == 'data_enlargeable'

    def test_add_data(self, get_h5saver):
        h5saver = get_h5saver
        data_saver = DataEnlargeableSaverLoader(h5saver)
        Ndata = 2

        data = DataWithAxes(name='mydata', data=[DATA2D for _ in range(Ndata)], labels=['mylabel1', 'mylabel2'],
                            source='raw',
                            dim='Data2D', distribution='uniform',
                            axes=[Axis(data=create_axis_array(DATA2D.shape[0]), label='myaxis0', units='myunits0',
                                       index=0),
                                  Axis(data=create_axis_array(DATA2D.shape[1]), label='myaxis1', units='myunits1',
                                       index=1),])

        data_saver.add_data(h5saver.raw_group, data)
        assert len(data_saver.get_axes(h5saver.raw_group)) == Ndata
        data_node = h5saver.get_node('/RawData/EnlData00')

        ESHAPE = [1]
        ESHAPE += list(DATA2D.shape)
        assert data_node.attrs['shape'] == tuple(ESHAPE)
        data_saver.add_data(h5saver.raw_group, data)
        ESHAPE = [2]
        ESHAPE += list(DATA2D.shape)
        assert data_node.attrs['shape'] == tuple(ESHAPE)

        data_loaded = data_saver.load_data(h5saver.get_node('/RawData/EnlData00'))
        for ind in range(len(data_loaded)):
            assert np.all(data_loaded[ind][0] == pytest.approx(DATA2D))
            assert np.all(data_loaded[ind][1] == pytest.approx(DATA2D))


class TestDataToExportSaverLoader:
    def test_save(self, get_h5saver):
        h5saver = get_h5saver
        Ndata = 2
        data_saver = DataToExportSaverLoader(h5saver)
        data2D = DataWithAxes(name='mydata2D', data=[DATA2D for _ in range(Ndata)], labels=['mylabel1', 'mylabel2'],
                              source='raw',
                            dim='Data2D', distribution='uniform',
                              axes=[Axis(data=create_axis_array(DATA2D.shape[0]), label='myaxis0', units='myunits0',
                                         index=0),
                                    Axis(data=create_axis_array(DATA2D.shape[1]), label='myaxis1', units='myunits1',
                                         index=1), ])

        data1D = DataWithAxes(name='mydata1D', data=[DATA1D for _ in range(Ndata)], labels=['mylabel1', 'mylabel2'],
                              source='raw',
                              dim='Data1D', distribution='uniform',
                              axes=[Axis(data=create_axis_array(DATA1D.shape[0]), label='myaxis0', units='myunits0',
                                         index=0)])

        data0D = DataWithAxes(name='mydata0D', data=[DATA0D for _ in range(Ndata)], labels=['mylabel1', 'mylabel2'],
                              source='raw', dim='Data0D', distribution='uniform')

        data0Dbis = DataWithAxes(name='mydata0Dbis', data=[DATA0D for _ in range(Ndata)],
                                 labels=['mylabel1', 'mylabel2'], source='raw', dim='Data0D', distribution='uniform')

        data_to_export = DataToExport(name='mybigdata', data=[data2D, data0D, data1D, data0Dbis])

        det_group = h5saver.get_set_group(h5saver.raw_group, 'MyDet')

        data_saver.add_data(det_group, data_to_export)
        data_loaded = data_saver.load_data(h5saver.get_node('/RawData/MyDet/Data2D/CH00/Data00'))
        for ind in range(len(data_loaded)):
            assert np.all(data_loaded[ind] == pytest.approx(DATA2D))


class TestDataToExportEnlargeableLoaderSaver:
    def test_save_load(self, get_h5saver):
        h5saver = get_h5saver
        Ndata = 2
        data_saver = DataToExportEnlargeableLoaderSaver(h5saver)
        data2D = DataWithAxes(name='mydata2D', data=[DATA2D for _ in range(Ndata)], labels=['mylabel1', 'mylabel2'],
                              source='raw',
                              dim='Data2D', distribution='uniform',
                              axes=[Axis(data=create_axis_array(DATA2D.shape[0]), label='myaxis0', units='myunits0',
                                         index=0),
                                    Axis(data=create_axis_array(DATA2D.shape[1]), label='myaxis1', units='myunits1',
                                         index=1), ])

        data1D = DataWithAxes(name='mydata1D', data=[DATA1D for _ in range(Ndata)], labels=['mylabel1', 'mylabel2'],
                              source='raw',
                              dim='Data1D', distribution='uniform',
                              axes=[Axis(data=create_axis_array(DATA1D.shape[0]), label='myaxis0', units='myunits0',
                                         index=0)])

        data0D = DataWithAxes(name='mydata0D', data=[DATA0D for _ in range(Ndata)], labels=['mylabel1', 'mylabel2'],
                              source='raw', dim='Data0D', distribution='uniform')

        data0Dbis = DataWithAxes(name='mydata0Dbis', data=[DATA0D for _ in range(Ndata)],
                                 labels=['mylabel1', 'mylabel2'], source='raw', dim='Data0D', distribution='uniform')

        data_to_export = DataToExport(name='mybigdata', data=[data2D, data0D, data1D, data0Dbis])

        det_group = h5saver.get_set_group(h5saver.raw_group, 'MyDet')

        data_saver.add_data(det_group, data_to_export)
        data_saver.add_data(det_group, data_to_export)

        assert data_saver.get_nav_group('/RawData/MyDet/Data2D/CH00/EnlData00') == \
               h5saver.get_node(f'/RawData/MyDet/{data_saver._nav_axes_name}')

        data_loaded = data_saver.load_data('/RawData/MyDet/Data2D/CH00/EnlData00')
        for ind in range(len(data_loaded)):
            assert np.all(data_loaded[ind][0] == pytest.approx(DATA2D))
            assert np.all(data_loaded[ind][1] == pytest.approx(DATA2D))
