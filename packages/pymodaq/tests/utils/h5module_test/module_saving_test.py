# -*- coding: utf-8 -*-
"""
Created the 23/11/2022

@author: Sebastien Weber
"""

import numpy as np
import pytest

from pymodaq_data.h5modules.saving import H5SaverLowLevel
from pymodaq_data.h5modules import backends
from pymodaq.utils.h5modules.module_saving import DetectorSaver, ScanSaver, GroupModuleType, TimeModuleSaver

from pymodaq_gui.parameter import Parameter
from pymodaq.control_modules.mocks import MockScan, MockDAQMove, MockDAQViewer

tested_backend = [b for b in ['tables', 'h5py'] if b in backends.backends_available]


@pytest.fixture(params=tested_backend)
def h5saver_with_settings(request, tmp_path):
    h5saver = H5SaverLowLevel(backend=request.param)
    addhoc_file_path = tmp_path.joinpath('h5file.h5')
    h5saver.init_file(file_name=addhoc_file_path)
    params = [{'title': 'mysaver', 'name': 'saver', 'type': 'str', 'value': 'myh5saver'}]
    h5saver.settings = Parameter.create(name='settings', type='group', children=params)  # create a Parameter
    yield h5saver
    h5saver.close_file()


class TestDetectorSaver:
    def test_get_set_node(self, h5saver_with_settings):
        h5saver = h5saver_with_settings
        mock_det = MockDAQViewer(h5saver)
        det_saver = DetectorSaver(module=mock_det)
        det_saver.h5saver = h5saver

        assert det_saver.group_type == GroupModuleType.DETECTOR

        for node in h5saver.walk_nodes('/'):
            assert 'detector' not in node.attrs

        node0 = det_saver.get_set_node()
        assert node0.attrs['TITLE'] == 'MyDet0D'
        assert node0.title == 'MyDet0D'
        assert node0.name == 'Detector000'

        node1 = det_saver.get_set_node()
        assert node1 == node0


class TestScanSaver:
    def test_get_set_node(self, h5saver_with_settings):
        h5saver = h5saver_with_settings
        mock_scan_module = MockScan(h5saver)
        scan_saver = ScanSaver(module=mock_scan_module)
        scan_saver.h5saver = h5saver

        assert scan_saver.group_type == GroupModuleType.SCAN

        for node in h5saver.walk_nodes('/'):
            assert 'scan' not in node.attrs

        node0 = scan_saver.get_set_node()
        assert node0.attrs['TITLE'] == 'MyScan'
        assert node0.title == 'MyScan'
        assert node0.name == 'Scan000'
        assert len(node0.children_name())-1 == len(mock_scan_module.modules_manager.modules_all)  # -1 because of the Timestamps node
        assert node0.children_name() == ['Actuator000', 'Detector000', 'Detector001', 'Timestamps']
        assert node0.get_child('Actuator000').title == 'MyAct'

        node1 = scan_saver.get_set_node()
        assert node1 == node0

        node2 = scan_saver.get_set_node(new=True)
        assert node2 != node0
        assert node2.name == 'Scan001'
        assert node2.children_name() == ['Actuator000', 'Detector000', 'Detector001', 'Timestamps']
        assert node2.get_child('Actuator000').title == 'MyAct'

        node3 = scan_saver.get_set_node()
        assert node3 == node2


class TestTimeModuleSaver:
    def test_timestamps_initialized_with_nan(self, h5saver_with_settings):
        """All unwritten positions of the timestamp array are NaN."""
        h5saver = h5saver_with_settings
        ts_saver = TimeModuleSaver()
        ts_saver.h5saver = h5saver

        scan_group = h5saver.get_set_group(h5saver.raw_group, 'Scan000')
        ts_saver.get_set_node(scan_group)

        EXT_SHAPE = (4,)
        ts_saver.initialize(EXT_SHAPE)
        # Trigger array creation by writing one point
        ts_saver.add_time((0,))

        node = h5saver.get_node('/RawData/Scan000/Timestamps/Data0D/CH00/Data00')
        arr = node.read()
        assert arr.shape == EXT_SHAPE
        # Index 0 was written (finite); indices 1-3 must be NaN
        assert np.isfinite(arr[0])
        assert np.all(np.isnan(arr[1:]))

    def test_timestamps_written_value(self, h5saver_with_settings):
        """Written timestamp is finite and at the correct index; unwritten stay NaN."""
        h5saver = h5saver_with_settings
        ts_saver = TimeModuleSaver()
        ts_saver.h5saver = h5saver

        scan_group = h5saver.get_set_group(h5saver.raw_group, 'Scan000')
        ts_saver.get_set_node(scan_group)

        EXT_SHAPE = (5,)
        ts_saver.initialize(EXT_SHAPE)

        ts_saver.add_time((2,))

        node = h5saver.get_node('/RawData/Scan000/Timestamps/Data0D/CH00/Data00')
        arr = node.read()
        assert np.isfinite(arr[2])
        assert arr[2] >= 0.0
        assert np.isnan(arr[0])
        assert np.isnan(arr[1])
        assert np.isnan(arr[3])
        assert np.isnan(arr[4])

    def test_timestamps_multiple_writes(self, h5saver_with_settings):
        """Multiple writes populate the correct positions; unvisited stay NaN."""
        h5saver = h5saver_with_settings
        ts_saver = TimeModuleSaver()
        ts_saver.h5saver = h5saver

        scan_group = h5saver.get_set_group(h5saver.raw_group, 'Scan000')
        ts_saver.get_set_node(scan_group)

        EXT_SHAPE = (6,)
        ts_saver.initialize(EXT_SHAPE)

        for idx in [1, 3, 5]:
            ts_saver.add_time((idx,))

        node = h5saver.get_node('/RawData/Scan000/Timestamps/Data0D/CH00/Data00')
        arr = node.read()
        for idx in [1, 3, 5]:
            assert np.isfinite(arr[idx])
            assert arr[idx] >= 0.0
        for idx in [0, 2, 4]:
            assert np.isnan(arr[idx])

