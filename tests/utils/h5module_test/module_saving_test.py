# -*- coding: utf-8 -*-
"""
Created the 23/11/2022

@author: Sebastien Weber
"""

import numpy as np
import pytest

from pymodaq.utils.h5modules import saving
from pymodaq.utils.h5modules.module_saving import DetectorSaver, ActuatorSaver, ScanSaver
from pymodaq.utils.h5modules.data_saving import DataManagement, AxisSaverLoader, DataSaverLoader, DataToExportSaver
from pymodaq.utils.data import Axis, DataWithAxes, DataSource, DataToExport
from pymodaq.utils.parameter import Parameter
from pymodaq.control_modules.mocks import MockScan, MockDAQMove, MockDAQViewer

@pytest.fixture()
def get_h5saver_module(tmp_path):
    h5saver = saving.H5SaverLowLevel()
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

        assert det_saver.group_type.name == 'detector'

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

        assert scan_saver.group_type.name == 'scan'

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


