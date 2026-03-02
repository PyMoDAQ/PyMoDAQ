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
from pymodaq_utils.config import GlobalConfig

from pymodaq_data.data import DataDim

config = GlobalConfig()
tested_backend = [b for b in ['tables', 'h5py'] if b in backends.backends_available]


@pytest.fixture(scope="module")
def session_path(tmp_path_factory):
    return tmp_path_factory.mktemp('h5data')


def generate_random_data(shape, dtype=float):
    return (100 * np.random.rand(*shape)).astype(dtype=dtype)


class TestH5SaverLowLevel:

    @pytest.mark.parametrize('backend', tested_backend)
    def test_init_file(self, tmp_path, backend):
        h5saver = saving.H5SaverLowLevel(backend=backend)
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

    def test_logger(self, h5saver_lowlevel):
        h5saver = h5saver_lowlevel

        LOGS = ['This', 'is', 'a', 'message']
        for log in LOGS:
            h5saver.add_log(log)

        logger_array = h5saver.get_set_logger()

        assert logger_array.read() == LOGS

    def test_add_string_array(self, h5saver_lowlevel):
        #todo
        pass

    def test_add_array_default_fill_is_from_config(self, h5saver_lowlevel):
        h5saver = h5saver_lowlevel
        config_value_str = config('data', 'data_saving', 'data_type', 'fill_value')[0]
        if config_value_str == '0':
            config_value = 0.
            assert h5saver.fill_value == config_value
        elif config_value_str == 'nan':
            config_value = np.nan
            assert h5saver.fill_value is config_value
        else:
            raise ValueError

        array = h5saver.add_array(h5saver.raw_group, 'TestArray', saving.DataType['data'],
                                  data_dimension = DataDim['Data0D'],
                                  data_shape=(4,), array_type=np.float64,
                                  scan_shape=(3,), add_scan_dim=True)
        if config_value_str == 'nan':
            assert np.all(np.isnan(array.read()))
        elif config_value_str == '0':
            assert np.allclose(array.read(), config_value)

    def test_add_array_explicit_fill_value(self, h5saver_lowlevel):
        h5saver = h5saver_lowlevel
        array = h5saver.add_array(h5saver.raw_group, 'TestFill', saving.DataType['data'],
                                  data_dimension = DataDim['Data0D'],
                                  data_shape=(4,), array_type=np.float64,
                                  scan_shape=(3,), add_scan_dim=True,
                                  fill_value=7.5)
        assert np.all(array.read() == pytest.approx(7.5))

    def test_add_array_nan_fill_value(self, h5saver_lowlevel):
        h5saver = h5saver_lowlevel
        array = h5saver.add_array(h5saver.raw_group, 'TestNan', saving.DataType['data'],
                                  data_dimension = DataDim['Data0D'],
                                  data_shape=(4,), array_type=np.float64,
                                  scan_shape=(3,), add_scan_dim=True,
                                  fill_value=np.nan)
        assert np.all(np.isnan(array.read()))

    def test_add_array_instance_fill_value_as_default(self, h5saver_lowlevel):
        """Setting h5saver.fill_value acts as the default for all subsequent add_array calls."""
        h5saver = h5saver_lowlevel
        h5saver.fill_value = np.nan
        array = h5saver.add_array(h5saver.raw_group, 'TestInstanceFill', saving.DataType['data'],
                                  data_dimension = DataDim['Data0D'],
                                  data_shape=(4,), array_type=np.float64,
                                  scan_shape=(3,), add_scan_dim=True)
        assert np.all(np.isnan(array.read()))

    def test_add_array_explicit_fill_overrides_instance(self, h5saver_lowlevel):
        """An explicit fill_value argument takes precedence over h5saver.fill_value."""
        h5saver = h5saver_lowlevel
        h5saver.fill_value = np.nan
        array = h5saver.add_array(h5saver.raw_group, 'TestOverride', saving.DataType['data'],
                                  data_dimension = DataDim['Data0D'],
                                  data_shape=(4,), array_type=np.float64,
                                  scan_shape=(3,), add_scan_dim=True,
                                  fill_value=0.0)
        assert np.allclose(array.read(), 0.0)

    def test_incremental_group(self, h5saver_lowlevel):
        # "todo
        h5saver = h5saver_lowlevel

