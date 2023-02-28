# -*- coding: utf-8 -*-
"""
Created the 21/11/2022

@author: Sebastien Weber
"""
import numpy as np
import pytest
from datetime import datetime

from pymodaq.utils.h5modules import saving
from pymodaq.utils import daq_utils as utils
from pymodaq.utils.h5modules.data_saving import DataManagement, AxisSaverLoader
from pymodaq.utils.daq_utils import capitalize


tested_backend = ['tables', 'h5py']  # , 'h5pyd']


@pytest.fixture()
def get_h5saver_lowlevel(tmp_path):
    h5saver = saving.H5SaverLowLevel()
    addhoc_file_path = tmp_path.joinpath('h5file.h5')
    h5saver.init_file(file_name=addhoc_file_path, file_type=saving.FileType['detector'])

    yield h5saver
    h5saver.close_file()


@pytest.fixture()
def get_h5saver(qtbot):
    h5saver = saving.H5Saver()
    yield h5saver
    h5saver.close_file()


@pytest.fixture(params=tested_backend)
def get_h5saver_scan(request, qtbot):
    return saving.H5Saver(save_type='scan', backend=request.param)


@pytest.fixture(scope="module")
def session_path(tmp_path_factory):
    return tmp_path_factory.mktemp('h5data')


def generate_random_data(shape, dtype=float):
    return (100 * np.random.rand(*shape)).astype(dtype=dtype)


class TestH5SaverLowLevel:

    def test_init_file(self, tmp_path):
        h5saver = saving.H5SaverLowLevel()
        addhoc_file_path = tmp_path.joinpath('h5file.h5')
        h5saver.init_file(file_name=addhoc_file_path, file_type=saving.FileType['detector'],
                          metadata=dict(attr1='attr1', attr2=(10, 2)))

        assert h5saver.h5_file_path == addhoc_file_path.parent
        assert h5saver.h5_file_name == addhoc_file_path.name

        assert h5saver.get_node_path(h5saver.raw_group) == '/RawData'
        assert h5saver.get_node_path(h5saver._logger_array) == '/RawData/Logger'
        h5saver.close_file()

    def test_logger(self, get_h5saver_lowlevel):
        h5saver = get_h5saver_lowlevel

        LOGS = ['This', 'is', 'a', 'message']
        for log in LOGS:
            h5saver.add_log(log)

        assert h5saver._logger_array.read() == LOGS

    def test_add_string_array(self, get_h5saver_lowlevel):
        #todo
        pass

    def test_add_array(self, get_h5saver_lowlevel):
        #"todo
        pass

    def test_incremental_group(self, get_h5saver_lowlevel):
        # "todo
        h5saver = get_h5saver_lowlevel


class TestH5Saver:

    def test_init_file_addhoc(self, get_h5saver, tmp_path):
        h5saver = get_h5saver
        addhoc_file_path = tmp_path.joinpath('h5file.h5')
        h5saver.init_file(update_h5=True, addhoc_file_path=addhoc_file_path,
                          metadata=dict(attr1='attr1', attr2=(10, 2)))
        assert h5saver.h5_file_path == addhoc_file_path.parent
        assert h5saver.h5_file_name == addhoc_file_path.name
        assert h5saver.settings['current_h5_file'] == str(addhoc_file_path)
        assert h5saver.current_scan_group is None
        assert h5saver.get_node_path(h5saver.raw_group) == '/RawData'
        logger_array = h5saver.get_set_logger()
        assert h5saver.get_node_path(logger_array) == '/RawData/Logger'
        assert h5saver.get_attr(logger_array, 'type') == 'log'
        assert h5saver.get_attr(logger_array, 'data_type') == 'strings'
        assert h5saver.get_attr(logger_array, 'dtype') == np.dtype(np.uint8).name
        assert h5saver.get_attr(logger_array, 'subdtype') == 'string'
        assert h5saver.get_last_scan() is None
        assert h5saver.get_attr(h5saver.raw_group, 'type') == h5saver.settings['save_type']
        assert h5saver.get_attr(h5saver.root(), 'date') == datetime.now().date().isoformat()
        assert h5saver.get_attr(h5saver.raw_group, 'attr1') == 'attr1'
        utils.check_vals_in_iterable(h5saver.get_attr(h5saver.raw_group, 'attr2'), (10, 2))

    def test_init_file(self, get_h5saver_scan, tmp_path):
        h5saver = get_h5saver_scan
        datetime_now = datetime.now()
        date = datetime_now.date()
        today = f'{date.year}{date.month:02d}{date.day:02d}'
        base_path = tmp_path
        h5saver.settings.child(('base_path')).setValue(str(base_path))
        update_h5 = True
        scan_path, current_scan_name, save_path = h5saver.update_file_paths(update_h5)
        assert scan_path == tmp_path.joinpath(str(date.year)).joinpath(today).joinpath(f'Dataset_{today}_000')
        assert current_scan_name == 'Scan000'

        assert save_path == tmp_path.joinpath(str(date.year)).joinpath(today).joinpath(f'Dataset_{today}_000')

        h5saver.init_file(update_h5=update_h5)
        assert h5saver.h5_file is h5saver._h5file
        # assert h5saver.h5_file_path.joinpath(f'Dataset_{today}_001.h5').is_file()
        assert h5saver.get_scan_index() == 0

        h5saver.init_file(update_h5=update_h5)
        assert h5saver.h5_file_path.joinpath(f'Dataset_{today}_000.h5').is_file()
        scan_group = h5saver.add_scan_group()
        assert h5saver.get_node_name(h5saver.get_last_scan()) == 'Scan000'
        assert h5saver.get_scan_index() == 0
        scan_group1 = h5saver.add_scan_group()
        assert scan_group == scan_group1  # no increment as no scan_done attribute
        utils.check_vals_in_iterable(sorted(list(h5saver.get_children(h5saver.raw_group))),
                                     sorted(['Logger', 'Scan000']))
        h5saver.init_file(update_h5=False)
        utils.check_vals_in_iterable(sorted(list(h5saver.get_children(h5saver.raw_group))),
                                     sorted(['Logger', 'Scan000']))

    def test_load_file(self, get_h5saver_scan, tmp_path):
        h5saver = get_h5saver_scan
        h5saver.settings.child(('base_path')).setValue(str(tmp_path))
        h5saver.init_file(update_h5=True)
        h5saver.close_file()
        file_path = h5saver.settings.child(('current_h5_file')).value()

        h5saver.load_file(file_path=file_path)
        assert h5saver.file_loaded

    def test_groups(self, get_h5saver_scan, tmp_path):
        h5saver = get_h5saver_scan
        base_path = tmp_path
        h5saver.settings.child(('base_path')).setValue(base_path)
        update_h5 = True
        h5saver.init_file(update_h5=update_h5)
        scan_group = h5saver.add_scan_group(settings_as_xml='this is a setting',
                                            metadata=dict(attr1='blabla', attr2=1.1, pixmap2D='invalid pixmap'))
        assert h5saver.get_scan_index() == 0
        assert h5saver.get_node_name(h5saver.get_last_scan()) == 'Scan000'
        scan_group = h5saver.add_scan_group()
        # if no child in scan group no incrementation
        assert h5saver.get_scan_index() == 0
        assert h5saver.get_node_name(h5saver.get_last_scan()) == 'Scan000'

        ch1_group = h5saver.add_CH_group(scan_group)
        assert h5saver.get_node_path(ch1_group) == '/Raw_datas/Scan000/Ch000'
        assert h5saver.get_set_group(scan_group, 'Ch000') == h5saver.current_group
        assert h5saver.get_scan_index() == 0
        h5saver.set_attr(scan_group, 'scan_done', True)
        assert h5saver.get_scan_index() == 1

        scan_group_1 = h5saver.add_scan_group()
        assert h5saver.get_scan_index() == 1
        h5saver.set_attr(scan_group_1, 'scan_done', True)
        assert h5saver.get_scan_index() == 2
        ch1_group_1 = h5saver.add_CH_group(scan_group_1)
        assert h5saver.get_scan_index() == 2
        assert h5saver.get_node_name(h5saver.get_last_scan()) == 'Scan001'

    def test_hierarchy(self, get_h5saver_scan, tmp_path):
        h5saver = get_h5saver_scan
        base_path = tmp_path
        h5saver.settings.child(('base_path')).setValue(base_path)
        h5saver.init_file(update_h5=True)
        scan_group = h5saver.add_scan_group()
        h5saver.add_det_group(scan_group)
        h5saver.add_det_group(scan_group)
        move_group = h5saver.add_move_group(scan_group)
        assert h5saver.get_node_path(move_group) == '/Raw_datas/Scan000/Move000'
        det_group = h5saver.add_det_group(scan_group)
        for data_type in h5modules.group_data_types:
            data_group = h5saver.add_data_group(det_group, data_type)
            assert h5saver.get_node_name(data_group) == utils.capitalize(data_type)
            CH_group0 = h5saver.add_CH_group(data_group)
            assert h5saver.get_node_path(
                CH_group0) == f'/Raw_datas/Scan000/Detector002/{utils.capitalize(data_type)}/Ch000'
            CH_group1 = h5saver.add_CH_group(data_group)
            assert h5saver.get_node_path(
                CH_group1) == f'/Raw_datas/Scan000/Detector002/{utils.capitalize(data_type)}/Ch001'

        live_group = h5saver.add_live_scan_group(scan_group, '0D')
        assert h5saver.get_node_path(live_group) == '/Raw_datas/Scan000/Live_scan_0D'

    def test_data_save(self, get_h5saver_scan, tmp_path):
        h5saver = get_h5saver_scan
        base_path = tmp_path
        h5saver.settings.child(('base_path')).setValue(base_path)
        h5saver.init_file(update_h5=True)
        scan_group = h5saver.add_scan_group()
        det_group = h5saver.add_det_group(scan_group)
        data_group = h5saver.add_data_group(det_group, 'data2D')
        CH_group0 = h5saver.add_CH_group(data_group)
        CH_group1 = h5saver.add_CH_group(data_group)

        xaxis = dict(data=np.linspace(0, 5, 6), label='x_axis_label', units='x_axis_units')
        yaxis = dict(data=np.linspace(10, 20, 11), label='y_axis_label', units='custom')
        data_dict = dict(data=np.random.rand(len(xaxis['data']), len(yaxis['data'])), x_axis=xaxis,
                         y_axis=yaxis)
        array = h5saver.add_data(CH_group0, data_dict, scan_type='', enlargeable=False)
        assert h5saver.is_node_in_group(CH_group0, 'Data')
        assert np.all(h5saver.get_attr(array, 'shape') == data_dict['data'].shape)
        assert array.attrs['type'] == 'data'
        assert h5saver.get_attr(array, 'data_dimension') == '2D'
        assert array.attrs['scan_type'] == ''

        nav_x_axis = dict(data=np.linspace(0, 2, 3), label='navigation', units='custom')
        data_dict = dict(data=np.random.rand(len(xaxis['data']), len(yaxis['data'])), x_axis=xaxis,
                         y_axis=yaxis, nav_x_axis=nav_x_axis)

        array = h5saver.add_data(CH_group1, data_dict, init=True, scan_type='scan1D',
                                 scan_shape=nav_x_axis['data'].shape,
                                 enlargeable=False, add_scan_dim=True)
        assert h5saver.is_node_in_group(CH_group1, 'Data')
        assert np.all(h5saver.get_attr(array, 'shape') == (len(nav_x_axis['data']),
                                                           len(xaxis['data']), len(yaxis['data'])))
        assert array.attrs['type'] == 'data'
        assert array.attrs['data_dimension'] == '2D'
        assert array.attrs['scan_type'] == 'scan1D'
        assert np.all(h5saver.read(array).shape == (len(nav_x_axis['data']), len(xaxis['data']), len(yaxis['data'])))
        assert h5saver.is_node_in_group(CH_group1, 'X_axis')
        xnode = h5saver.get_node(CH_group1, 'X_axis')
        assert xnode.attrs['type'] == 'axis'
        assert xnode.attrs['label'] == 'x_axis_label'
        assert xnode.attrs['units'] == 'x_axis_units'
        assert xnode.attrs['data_dimension'] == '1D'
        assert xnode.attrs['scan_type'] == ''

        assert h5saver.is_node_in_group(CH_group1, 'Y_axis')

        assert h5saver.is_node_in_group(CH_group1, 'Nav_x_axis')
        navnode = h5saver.get_node(CH_group1, 'Nav_x_axis')
        assert navnode.attrs['type'] == 'axis'
        assert navnode.attrs['label'] == 'navigation'
        assert navnode.attrs['units'] == 'custom'
        assert navnode.attrs['data_dimension'] == '1D'
        assert navnode.attrs['scan_type'] == ''

        # test enlargeable array
        CH_group2 = h5saver.add_CH_group(data_group)
        dshape = (10,)
        array = h5saver.add_array(CH_group2, 'earray', data_type='data', data_shape=dshape, data_dimension='1D',
                                  array_type=np.uint32,
                                  enlargeable=True)
        assert h5saver.is_node_in_group(CH_group2, 'earray')
        assert array.attrs['CLASS'] == 'EARRAY'
        array.append(np.random.rand(*dshape))
        array.append(np.random.rand(*dshape))
        assert np.all(h5saver.read(array).shape == (2, 10))

