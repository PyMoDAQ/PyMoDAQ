# -*- coding: utf-8 -*-
"""
Created the 21/11/2022

@author: Sebastien Weber
"""
import numpy as np
import pytest

from pymodaq.utils.h5modules import saving
from pymodaq.utils.h5modules.data_saving import DataSaver, AxisSaverLoader
from pymodaq.utils.daq_utils import capitalize


tested_backend = ['tables', 'h5py']  # , 'h5pyd']


@pytest.fixture()
def get_h5saver(tmp_path):
    h5saver = saving.H5SaverLowLevel()
    addhoc_file_path = tmp_path.joinpath('h5file.h5')
    h5saver.init_file(file_name=addhoc_file_path, file_type=saving.FileType['detector'])

    yield h5saver
    h5saver.close_file()


@pytest.fixture(scope="module")
def session_path(tmp_path_factory):
    return tmp_path_factory.mktemp('h5data')


def generate_random_data(shape, dtype=float):
    return (100 * np.random.rand(*shape)).astype(dtype=dtype)


class NoAttribute(DataSaver):
    pass


class EnumAttribute(DataSaver):
    data_type = saving.DataType(0)


class StrAttribute(DataSaver):
    data_type = saving.DataType.names()[2]


class UnknownStrAttribute(DataSaver):
    data_type = 'azertyuiop'


class TestSaver:
    def test_class_attribute(self):
        with pytest.raises(NotImplementedError):
            NoAttribute()

        ea = EnumAttribute()
        assert ea.data_type == saving.DataType(0)

        sa = StrAttribute()
        assert sa.data_type == saving.DataType.names()[2]

        with pytest.raises(ValueError):
            ua = UnknownStrAttribute()

    def test_format(self):

        assert EnumAttribute._format_node_name(24) == f'{capitalize(EnumAttribute.data_type.name)}{24:02d}'


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

    def test_logger(self, get_h5saver):
        h5saver = get_h5saver

        LOGS = ['This', 'is', 'a', 'message']
        for log in LOGS:
            h5saver.add_log(log)

        assert h5saver._logger_array.read() == LOGS

    def test_add_string_array(self, get_h5saver):
        #todo
        pass

    def test_add_array(self, get_h5saver):
        #"todo
        pass

    def test_incrmental_group(self, get_h5saver):
        # "todo
        h5saver = get_h5saver
