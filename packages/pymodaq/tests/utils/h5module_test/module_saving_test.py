# -*- coding: utf-8 -*-
"""
Created the 23/11/2022

@author: Sebastien Weber
"""

import numpy as np
import pytest

from pymodaq_data.h5modules.saving import H5SaverLowLevel
from pymodaq.utils.h5modules.module_saving import DetectorSaver, ScanSaver, GroupModuleType, TimeModuleSaver

from pymodaq_gui.parameter import Parameter
from pymodaq.control_modules.mocks import MockScan, MockDAQMove, MockDAQViewer

@pytest.fixture()
def get_h5saver_module(tmp_path):
    h5saver = H5SaverLowLevel()
    addhoc_file_path = tmp_path.joinpath('h5file.h5')
    h5saver.init_file(file_name=addhoc_file_path)
    params = [{'title': 'mysaver', 'name': 'saver', 'type': 'str', 'value': 'myh5saver'}]
    h5saver.settings = Parameter.create(name='settings', type='group', children=params)  # create a Parameter
    yield h5saver
    h5saver.close_file()


class TestDetectorSaver:
    def test_get_set_node(self, get_h5saver_module):
        h5saver = get_h5saver_module
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
    def test_get_set_node(self, get_h5saver_module):
        h5saver = get_h5saver_module
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
        assert len(node0.children_name()) == len(mock_scan_module.modules_manager.modules_all)
        assert node0.children_name() == ['Actuator000', 'Detector000', 'Detector001']
        assert node0.get_child('Actuator000').title == 'MyAct'

        node1 = scan_saver.get_set_node()
        assert node1 == node0

        node2 = scan_saver.get_set_node(new=True)
        assert node2 != node0
        assert node2.name == 'Scan001'
        assert node2.children_name() == ['Actuator000', 'Detector000', 'Detector001']
        assert node2.get_child('Actuator000').title == 'MyAct'

        node3 = scan_saver.get_set_node()
        assert node3 == node2


class TestTimeModuleSaver:
    def test_timestamps_initialized_with_nan(self, get_h5saver_module):
        """All positions of the timestamp array are NaN before any data is written."""
        h5saver = get_h5saver_module
        ts_saver = TimeModuleSaver()
        ts_saver.h5saver = h5saver

        scan_group = h5saver.get_set_group(h5saver.raw_group, 'Scan000')
        ts_saver.get_set_node(scan_group)

        EXT_SHAPE = (4,)
        ts_saver.initialize(EXT_SHAPE)
        # Trigger array creation by writing one point
        ts_saver.add_time((0,), 0.0)

        node = h5saver.get_node('/RawData/Scan000/Timestamps/Data0D/CH00/Data00')
        arr = node.read()
        assert arr.shape == EXT_SHAPE
        # Index 0 was written; indices 1-3 must be NaN
        assert np.all(np.isnan(arr[1:]))

    def test_timestamps_written_value(self, get_h5saver_module):
        """Written timestamp replaces the NaN placeholder at the correct index."""
        h5saver = get_h5saver_module
        ts_saver = TimeModuleSaver()
        ts_saver.h5saver = h5saver

        scan_group = h5saver.get_set_group(h5saver.raw_group, 'Scan000')
        ts_saver.get_set_node(scan_group)

        EXT_SHAPE = (5,)
        ts_saver.initialize(EXT_SHAPE)

        ts_saver.add_time((2,), 3.14)

        node = h5saver.get_node('/RawData/Scan000/Timestamps/Data0D/CH00/Data00')
        arr = node.read()
        assert np.isfinite(arr[2])
        assert arr[2] == pytest.approx(np.float32(3.14), abs=1e-4)
        assert np.isnan(arr[0])
        assert np.isnan(arr[1])
        assert np.isnan(arr[3])
        assert np.isnan(arr[4])

    def test_timestamps_multiple_writes(self, get_h5saver_module):
        """Multiple writes populate the correct positions; unvisited stay NaN."""
        h5saver = get_h5saver_module
        ts_saver = TimeModuleSaver()
        ts_saver.h5saver = h5saver

        scan_group = h5saver.get_set_group(h5saver.raw_group, 'Scan000')
        ts_saver.get_set_node(scan_group)

        EXT_SHAPE = (6,)
        ts_saver.initialize(EXT_SHAPE)

        times = {1: 1.0, 3: 2.5, 5: 4.0}
        for idx, t in times.items():
            ts_saver.add_time((idx,), t)

        node = h5saver.get_node('/RawData/Scan000/Timestamps/Data0D/CH00/Data00')
        arr = node.read()
        for idx, t in times.items():
            assert arr[idx] == pytest.approx(np.float32(t), abs=1e-4)
        for idx in [0, 2, 4]:
            assert np.isnan(arr[idx])

