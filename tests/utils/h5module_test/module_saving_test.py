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


@pytest.fixture()
def get_h5saver(tmp_path):
    h5saver = saving.H5SaverLowLevel()
    addhoc_file_path = tmp_path.joinpath('h5file.h5')
    h5saver.init_file(file_name=addhoc_file_path)
    params = [{'title': 'mysaver', 'name': 'saver', 'type': 'str', 'value': 'myh5saver'}]
    h5saver.settings = Parameter.create(name='settings', type='group', children=params)  # create a Parameter
    yield h5saver
    h5saver.close_file()


class MockDAQViewer:
    params = [{'title': 'mytitle', 'name': 'title', 'type': 'str', 'value': 'myviewervalue'}]

    def __init__(self, h5saver):
        self.settings = Parameter.create(name='settings', type='group', children=self.params)  # create a Parameter
        self.h5saver = h5saver
        self.title = 'MyDet'
        self.module_and_data_saver = DetectorSaver(self)
        self.ui = None


class MockDAQMove:
    params = [{'title': 'mytitle', 'name': 'title', 'type': 'str', 'value': 'myactuatorvalue'}]

    def __init__(self, h5saver):
        self.settings = Parameter.create(name='settings', type='group', children=self.params)  # create a Parameter
        self.h5saver = h5saver
        self.title = 'MyAct'
        self.module_and_data_saver = ActuatorSaver(self)
        self.ui = None


class ModulesManagerMock:
    def __init__(self):
        self.modules_all = []
        self.modules = []


class MockScan:
    params = [{'title': 'mytitle', 'name': 'title', 'type': 'str', 'value': 'myactuatorvalue'}]

    def __init__(self, h5saver):
        self.settings = Parameter.create(name='settings', type='group', children=self.params)  # create a Parameter
        self.h5saver = h5saver
        self.title = 'MyScan'
        self.modules_manager = ModulesManagerMock()
        self.module_and_data_saver = ScanSaver(self)
        self.ui = None


class TestDetectorSaver:
    def test_get_set_node(self, get_h5saver):
        h5saver = get_h5saver
        mock_det = MockDAQViewer(h5saver)
        det_saver = DetectorSaver(module=mock_det)
        det_saver.h5saver = h5saver

        assert det_saver.group_type.name == 'detector'

        for node in h5saver.walk_nodes('/'):
            assert 'detector' not in node.attrs

        node0 = det_saver.get_set_node()
        assert node0.attrs['TITLE'] == 'MyDet'
        assert node0.title == 'MyDet'
        assert node0.name == 'Detector000'

        node1 = det_saver.get_set_node()
        assert node1 == node0


class TestScanSaver:
    def test_get_set_node(self, get_h5saver):
        h5saver = get_h5saver
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
        h5saver.add_det_group(node0, 'det1')
        h5saver.add_move_group(node0, 'act1')

        node1 = scan_saver.get_set_node()
        assert node1 == node0

        h5saver.add_det_group(node0, 'det1')
        h5saver.add_move_group(node0, 'act1')
        node0.attrs['scan_done'] = True  # so next call to get_set_node will increment the scan node

        node2 = scan_saver.get_set_node()
        assert node2 != node0
        assert node2.name == 'Scan001'

        node3 = scan_saver.get_set_node()
        assert node3 == node2

        node4 = scan_saver.get_set_node()
