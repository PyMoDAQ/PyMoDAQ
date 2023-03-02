# -*- coding: utf-8 -*-
"""
Created the 21/11/2022

@author: Sebastien Weber
"""
import numpy as np
import pytest
from datetime import datetime

from pymodaq.utils.h5modules import saving, backends
from pymodaq.utils import daq_utils as utils
from pymodaq.utils.h5modules.data_saving import DataManagement, AxisSaverLoader
from pymodaq.utils.daq_utils import capitalize
from pymodaq.utils.data import DataDim

tested_backend = ['tables', 'h5py']  # , 'h5pyd']


@pytest.fixture()
def get_h5saver_lowlevel(tmp_path):
    h5saver = saving.H5SaverLowLevel()
    addhoc_file_path = tmp_path.joinpath('h5file.h5')
    h5saver.init_file(file_name=addhoc_file_path, new_file=True)

    yield h5saver
    h5saver.close_file()


@pytest.fixture()
def get_h5saver(qtbot):
    h5saver = saving.H5Saver()
    yield h5saver
    h5saver.close_file()


@pytest.fixture(params=tested_backend)
def get_h5saver_scan(request, qtbot):
    saver = saving.H5Saver(save_type='scan', backend=request.param)
    yield saver
    saver.close_file()


@pytest.fixture(scope="module")
def session_path(tmp_path_factory):
    return tmp_path_factory.mktemp('h5data')


def generate_random_data(shape, dtype=float):
    return (100 * np.random.rand(*shape)).astype(dtype=dtype)


class TestH5SaverLowLevel:

    def test_init_file(self, tmp_path):
        h5saver = saving.H5SaverLowLevel()
        addhoc_file_path = tmp_path.joinpath('h5file.h5')
        metadata = dict(attr1='attr1', attr2=(10, 2))
        h5saver.init_file(file_name=addhoc_file_path, new_file=True, metadata=metadata)

        assert h5saver.h5_file_path == addhoc_file_path.parent
        assert h5saver.h5_file_name == addhoc_file_path.name

        assert h5saver.get_node_path(h5saver.raw_group) == '/RawData'
        assert h5saver.get_node_path(h5saver._logger_array) == '/RawData/Logger'

        for key, value in metadata.items():
            assert key in h5saver.raw_group.attrs
            assert h5saver.raw_group.attrs[key] == value

        h5saver.close_file()

        h5saver.init_file(file_name=addhoc_file_path, new_file=False)
        for key, value in metadata.items():
            assert key in h5saver.raw_group.attrs
            assert h5saver.raw_group.attrs[key] == value
        h5saver.close_file()

    def test_logger(self, get_h5saver_lowlevel):
        h5saver = get_h5saver_lowlevel

        LOGS = ['This', 'is', 'a', 'message']
        for log in LOGS:
            h5saver.add_log(log)

        logger_array = h5saver.get_set_logger()

        assert logger_array.read() == LOGS

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

        utils.check_vals_in_iterable(sorted(list(h5saver.get_children(h5saver.raw_group))),
                                     sorted(['Logger', 'Scan000', 'Scan001']))
        h5saver.init_file(update_h5=False)
        utils.check_vals_in_iterable(sorted(list(h5saver.get_children(h5saver.raw_group))),
                                     sorted(['Logger', 'Scan000', 'Scan001']))

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
        assert h5saver.get_scan_index() == 1
        assert h5saver.get_node_name(h5saver.get_last_scan()) == 'Scan001'

        ch1_group = h5saver.add_ch_group(scan_group)
        assert h5saver.get_node_path(ch1_group) == '/RawData/Scan001/Ch000'
        assert h5saver.get_set_group(scan_group, 'Ch000') == h5saver._current_group
        assert h5saver.get_scan_index() == 1

        scan_group_1 = h5saver.add_scan_group()
        assert h5saver.get_scan_index() == 2

    def test_hierarchy(self, get_h5saver_scan, tmp_path):
        h5saver = get_h5saver_scan
        base_path = tmp_path
        h5saver.settings.child('base_path').setValue(base_path)
        h5saver.init_file(update_h5=True)
        scan_group = h5saver.add_scan_group()
        h5saver.add_det_group(scan_group)
        h5saver.add_det_group(scan_group)
        move_group = h5saver.add_move_group(scan_group)
        assert h5saver.get_node_path(move_group) == '/RawData/Scan000/Actuator000'
        det_group = h5saver.add_det_group(scan_group)
        for data_dim in DataDim.names():
            data_group = h5saver.add_data_group(det_group, data_dim)
            assert h5saver.get_node_name(data_group) == utils.capitalize(data_dim)
            CH_group0 = h5saver.add_ch_group(data_group)
            assert h5saver.get_node_path(CH_group0) ==\
                   f'/RawData/Scan000/Detector002/{utils.capitalize(data_dim)}/Ch000'
            CH_group1 = h5saver.add_ch_group(data_group)
            assert h5saver.get_node_path(CH_group1) ==\
                   f'/RawData/Scan000/Detector002/{utils.capitalize(data_dim)}/Ch001'

