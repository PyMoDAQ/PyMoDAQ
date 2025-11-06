# -*- coding: utf-8 -*-
"""
Created the 21/11/2022

@author: Sebastien Weber
"""
import numpy as np
import pytest
from datetime import datetime

from pymodaq_data.h5modules import saving, backends
from pymodaq_utils import utils

from pymodaq_data.data import DataDim

tested_backend = ['tables', 'h5py']  # , 'h5pyd']


@pytest.fixture()
def get_h5saver_lowlevel(tmp_path):
    h5saver = saving.H5SaverLowLevel()
    addhoc_file_path = tmp_path.joinpath('h5file.h5')
    h5saver.init_file(file_name=addhoc_file_path, new_file=True)

    yield h5saver
    h5saver.close_file()


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

