# -*- coding: utf-8 -*-
"""
Created the 21/11/2022

@author: Sebastien Weber
"""
import numpy as np
import pytest
from pathlib import Path

from pymodaq.utils.h5modules import saving
from pymodaq.utils.h5modules.data_saving import (DataLoader, AxisSaverLoader,
                                                 DataSaverLoader, DataToExportSaver,
                                                 DataEnlargeableSaver, DataToExportTimedSaver,
                                                 SPECIAL_GROUP_NAMES, DataToExportExtendedSaver,
                                                 DataToExportEnlargeableSaver, DataExtendedSaver,
                                                 DataLoader, BkgSaver, squeeze, DataDim)
from pymodaq.utils.data import Axis, DataWithAxes, DataSource, DataToExport, DataRaw


@pytest.fixture()
def get_h5saver(tmp_path):
    h5saver = saving.H5SaverLowLevel()
    addhoc_file_path = tmp_path.joinpath('h5file.h5')
    h5saver.init_file(file_name=addhoc_file_path)

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


@pytest.fixture()
def init_data_to_export():
    Ndata = 2

    data2D = DataWithAxes(name='mydata2D', data=[DATA2D for _ in range(Ndata)], labels=['mylabel1', 'mylabel2'],
                          source='raw',
                          dim='Data2D', distribution='uniform',
                          axes=[Axis(data=create_axis_array(DATA2D.shape[0]), label='myaxis0', units='myunits0',
                                     index=0),
                                Axis(data=create_axis_array(DATA2D.shape[1]), label='myaxis1', units='myunits1',
                                     index=1), ],
                          errors=[np.random.random_sample(DATA2D.shape) for _ in range(Ndata)])

    data1D = DataWithAxes(name='mydata1D', data=[DATA1D for _ in range(Ndata)], labels=['mylabel1', 'mylabel2'],
                          source='raw',
                          dim='Data1D', distribution='uniform',
                          axes=[Axis(data=create_axis_array(DATA1D.shape[0]), label='myaxis0', units='myunits0',
                                     index=0)],
                          errors=None)

    data0D = DataWithAxes(name='mydata0D', data=[DATA0D for _ in range(Ndata)], labels=['mylabel1', 'mylabel2'],
                          source='raw', dim='Data0D', distribution='uniform',
                          errors=[np.random.random_sample(DATA0D.shape) for _ in range(Ndata)])

    data0Dbis = DataWithAxes(name='mydata0Dbis', data=[DATA0D for _ in range(Ndata)],
                             labels=['mylabel1bis', 'mylabel2bis'], source='raw', dim='Data0D',
                             distribution='uniform')

    data_to_export = DataToExport(name='mybigdata', data=[data2D, data0D, data1D, data0Dbis])
    return data_to_export


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
        assert axis_node.read() == pytest.approx(axis.get_data())

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
                                       index=1)])

        data_saver.add_data(h5saver.raw_group, data)
        assert len(data_saver.get_axes(h5saver.raw_group)) == Ndata
        for axis_in, axis_out in zip(data.axes, data_saver.get_axes(h5saver.raw_group)):
            assert axis_in == axis_out

    def test_add_data_with_errors(self, get_h5saver):
        h5saver = get_h5saver
        data_saver = DataSaverLoader(h5saver)
        Ndata = 2

        errors = [np.random.random_sample(DATA2D.shape) for _ in range(Ndata)]

        data = DataWithAxes(name='mydata', data=[DATA2D for _ in range(Ndata)], labels=['mylabel1', 'mylabel2'],
                            source='raw',
                            dim='Data2D', distribution='uniform',
                            axes=[Axis(data=create_axis_array(DATA2D.shape[0]), label='myaxis0', units='myunits0',
                                       index=0),
                                  Axis(data=create_axis_array(DATA2D.shape[1]), label='myaxis1', units='myunits1',
                                       index=1)],
                            errors=errors)

        data_saver.add_data(h5saver.raw_group, data)
        assert len(data_saver.get_axes(h5saver.raw_group)) == Ndata
        for axis_in, axis_out in zip(data.axes, data_saver.get_axes(h5saver.raw_group)):
            assert axis_in == axis_out

        assert np.all(errors[0] == data_saver._error_saver.get_node_from_index('/RawData', 0).read())
        assert np.all(errors[1] == data_saver._error_saver.get_node_from_index('/RawData', 1).read())


    def test_load_data(self, get_h5saver):
        h5saver = get_h5saver
        data_saver = DataSaverLoader(h5saver)
        Ndata = 2
        errors = [np.random.random_sample(DATA1D.shape) for _ in range(Ndata)]

        data = DataWithAxes(name='mydata', data=[DATA1D for _ in range(Ndata)], labels=['mylabel1', 'mylabel2'],
                            source='raw',
                            dim='Data2D', distribution='uniform',
                            axes=[Axis(data=create_axis_array(DATA1D.shape[0]), label='myaxis0', units='myunits0',
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

    def test_load_with_bkg(self, get_h5saver):
        h5saver = get_h5saver
        data_saver = DataSaverLoader(h5saver)
        bkgSaver = BkgSaver(h5saver)

        axes = [Axis(data=create_axis_array(DATA2D.shape[0]), label='myaxis0', units='myunits0',
                     index=0),
                Axis(data=create_axis_array(DATA2D.shape[1]), label='myaxis1', units='myunits1',
                     index=1), ]

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

    def test_extra_attributes_and_timestamping(self, get_h5saver):
        h5saver = get_h5saver
        data_saver = DataSaverLoader(h5saver)
        Ndata = 2

        data = DataWithAxes(name='mydata', data=[DATA2D for _ in range(Ndata)], labels=['mylabel1', 'mylabel2'],
                            source='raw',
                            dim='Data2D', distribution='uniform',
                            axes=[Axis(data=create_axis_array(DATA2D.shape[0]), label='myaxis0', units='myunits0',
                                       index=0),
                                  Axis(data=create_axis_array(DATA2D.shape[1]), label='myaxis1', units='myunits1',
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
    def test_load_data(self, get_h5saver):
        h5saver = get_h5saver
        bkgSaver = BkgSaver(h5saver)

        axes = [Axis(data=create_axis_array(DATA2D.shape[0]), label='myaxis0', units='myunits0',
                     index=0),
                Axis(data=create_axis_array(DATA2D.shape[1]), label='myaxis1', units='myunits1',
                     index=1), ]

        data_bkg = init_data(DATA2D, axes=axes, name='mykbg')
        bkgSaver.add_data(h5saver.raw_group, data_bkg)

        data_bkg_loaded = bkgSaver.load_data('/RawData/Bkg00')
        assert data_bkg_loaded == data_bkg


class TestDataEnlargeableSaver:
    def test_init(self, get_h5saver):
        h5saver = get_h5saver
        data_saver = DataEnlargeableSaver(h5saver)
        assert data_saver.data_type.value == 'EnlData'
        assert data_saver.data_type.name == 'data_enlargeable'

    @pytest.mark.parametrize('Nenl', [1, 2, 3])
    @pytest.mark.parametrize('data_array', [DATA0D, DATA1D, DATA2D])
    def test_add_data(self, get_h5saver, data_array, Nenl):
        h5saver = get_h5saver

        Ndata = 2

        axis_values = tuple(np.random.randn(Nenl))
        data_saver = DataEnlargeableSaver(h5saver,
                                          enl_axis_names=['ax' for _ in range(Nenl)],
                                          enl_axis_units=['units' for _ in range(Nenl)])

        data = DataWithAxes(name='mydata', data=[data_array for _ in range(Ndata)],
                            labels=['mylabel1', 'mylabel2'],
                            source='raw', distribution='uniform',)
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


class TestDataExtendedSaver:
    def test_init(self, get_h5saver):
        h5saver = get_h5saver
        EXT_SHAPE = (5, 10)
        data_saver = DataExtendedSaver(h5saver, EXT_SHAPE)
        assert data_saver.data_type.value == 'Data'
        assert data_saver.data_type.name == 'data'
        assert data_saver.extended_shape == EXT_SHAPE

    def test_add_data(self, get_h5saver):
        h5saver = get_h5saver

        EXT_SHAPE = (5, 10)
        data_saver = DataExtendedSaver(h5saver, EXT_SHAPE)

        Ndata = 2

        data = DataWithAxes(name='mydata', data=[DATA2D for _ in range(Ndata)], labels=['mylabel1', 'mylabel2'],
                            source='raw',
                            dim='Data2D', distribution='uniform',
                            axes=[Axis(data=create_axis_array(DATA2D.shape[0]), label='myaxis0', units='myunits0',
                                       index=0),
                                  Axis(data=create_axis_array(DATA2D.shape[1]), label='myaxis1', units='myunits1',
                                       index=1),])
        data_ext_shape = list(EXT_SHAPE)
        data_ext_shape.extend(data.shape)

        INDEXES = [4, 3]
        data_saver.add_data(h5saver.raw_group, data, indexes=INDEXES)
        assert len(data_saver.get_axes(h5saver.raw_group)) == Ndata
        for ind in range(len(data)):
            data_node = h5saver.get_node(f'/RawData/Data0{ind}')

            assert data_node.attrs['shape'] == tuple(data_ext_shape)
            assert np.all(data_node[tuple(INDEXES)] == pytest.approx(data[ind]))


class TestDataToExportSaver:
    def test_save(self, get_h5saver, init_data_to_export):
        h5saver = get_h5saver
        data_to_export = init_data_to_export

        data_saver = DataToExportSaver(h5saver)

        det_group = h5saver.get_set_group(h5saver.raw_group, 'MyDet')
        data_saver.add_data(det_group, data_to_export)


class TestDataToExportEnlargeableSaver:

    def test_save(self, get_h5saver, init_data_to_export):
        h5saver = get_h5saver
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
    def test_spread_data(self, get_h5saver, Nenl, data_array):
        h5saver = get_h5saver

        dte_saver = DataToExportEnlargeableSaver(h5saver,
                                                 enl_axis_names=['ax' for _ in range(Nenl)],
                                                 enl_axis_units=['units' for _ in range(Nenl)]
                                                 )
        dte_loader = DataLoader(h5saver)

        axis_values = list(np.random.randn(Nenl))

        dwa = DataRaw('dwa', data=[data_array],
                      distribution='spread',)
        dwa.create_missing_axes()

        dte = DataToExport('dte', data=[dwa])
        dte_saver.add_data(h5saver.raw_group, data=dte, axis_values=axis_values)

        data_loaded = dte_loader.load_data(
            f'/RawData/{DataDim.from_data_array(data_array).name}/CH00/EnlData00')
        assert data_loaded.inav[0] == dwa


class TestDataToExportTimedSaver:
    def test_save(self, get_h5saver, init_data_to_export):
        h5saver = get_h5saver
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
    def test_save(self, get_h5saver, init_data_to_export):
        h5saver = get_h5saver
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


class TestDataLoader:
    def test_load_normal_data(self, get_h5saver, init_data_to_export):
        h5saver = get_h5saver
        data_to_export = init_data_to_export
        data_loader = DataLoader(h5saver)

        data_saver = DataToExportSaver(h5saver)
        det_group = h5saver.get_set_group(h5saver.raw_group, 'MyDet')

        data_saver.add_data(det_group, data_to_export)

        data_loaded = data_loader.load_data(h5saver.get_node('/RawData/MyDet/Data2D/CH00/Data00'))
        assert len(data_loaded) == 1
        for ind in range(len(data_loaded)):
            assert np.all(data_loaded[ind] == pytest.approx(DATA2D))

    def test_load_one_node(self, get_h5saver, init_data_to_export):
        h5saver = get_h5saver
        data_to_export = init_data_to_export
        data_loader = DataLoader(h5saver)

        data_saver = DataToExportSaver(h5saver)
        det_group = h5saver.get_set_group(h5saver.raw_group, 'MyDet')
        data_saver.add_data(det_group, data_to_export)

        data_loaded = data_loader.load_data(h5saver.get_node('/RawData/MyDet/Data2D/CH00/Data00'))
        assert len(data_loaded) == 1

        data_loaded = data_loader.load_data(h5saver.get_node('/RawData/MyDet/Data2D/CH00/Data01'), load_all=True)
        assert len(data_loaded) == 2

    def test_load_normal_data_with_bkg(self, get_h5saver, init_data_to_export):
        h5saver = get_h5saver
        data_to_export = init_data_to_export
        data_loader = DataLoader(h5saver)

        data_saver = DataToExportSaver(h5saver)
        det_group = h5saver.get_set_group(h5saver.raw_group, 'MyDet')

        data_saver.add_data(det_group, data_to_export)
        data_saver.add_bkg(det_group, data_to_export)

        data_loaded = data_loader.load_data(h5saver.get_node('/RawData/MyDet/Data2D/CH00/Data00'), with_bkg=True)
        for ind in range(len(data_loaded)):
            assert np.all(data_loaded[ind] == pytest.approx(0 * DATA2D))

    def test_load_enlargeable_data(self, get_h5saver, init_data_to_export):
        h5saver = get_h5saver
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

    def test_load_all(self, get_h5saver, init_data_to_export):
        h5saver = get_h5saver
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