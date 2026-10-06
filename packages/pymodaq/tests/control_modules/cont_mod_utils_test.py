# -*- coding: utf-8 -*-
"""
Created the 15/11/2022

@author: Sebastien Weber
"""
import pytest

from pymodaq.control_modules import utils
from pymodaq.control_modules.utils import ControlModule, HardwareWorkerBase
from pymodaq.control_modules.plugin_base import PluginBase
from pymodaq.utils.caller import CallerInfo
from pymodaq_gui.plotting.data_viewers import ViewersEnum
from pymodaq.control_modules.enums import DAQTypesEnum


class TestDAQType:
    def test_daq_types_enum(self):
        for value in DAQTypesEnum.values():
            assert value in ViewersEnum.names()

    @pytest.mark.parametrize('daq_type_str, data_type_str, viewer_type_str', [('DAQ0D', 'Data0D', 'Viewer0D'),
                                                                              ('DAQ1D', 'Data1D', 'Viewer1D'),
                                                                              ('DAQ2D', 'Data2D', 'Viewer2D'),
                                                                              ('DAQND', 'DataND', 'ViewerND')])
    def test_to_data_type(self, daq_type_str, data_type_str, viewer_type_str):
        daq_type = DAQTypesEnum[daq_type_str]

        assert daq_type.to_daq_type() == daq_type_str
        assert daq_type.to_viewer_type() == viewer_type_str
        assert daq_type.to_data_type() == data_type_str


class FakeH5Saver:
    def __init__(self, current_h5_file='/tmp/data/Data_20260101.h5', is_open=True):
        self.settings = {'current_h5_file': current_h5_file}
        self.h5_file = True  # truthy: skip the real H5Saver's init_file auto-call
        self.is_open = is_open

    def isopen(self):
        return self.is_open


class FakeGroup:
    def __init__(self, name='/RawData/Detector000'):
        self.name = name


class ClosedGroup:
    """Node of a closed h5 file: reading its name fails"""
    @property
    def name(self):
        raise AttributeError("'NoneType' object has no attribute 'split'")


class FakeModuleSaver:
    def __init__(self, h5saver=None, module_group=None):
        self.h5saver = h5saver
        self.module_group = module_group


class TestControlModuleGetCaller:
    def test_no_saver_returns_none(self, qtbot):
        cm = ControlModule()
        assert cm.get_caller() is None

    def test_saver_without_h5saver_does_not_create_a_file(self, qtbot):
        # get_caller is read-only: it must not go through the module_and_data_saver property,
        # which would create/open this module's own h5 file
        cm = ControlModule()
        cm._module_and_data_saver = FakeModuleSaver(h5saver=None)

        caller = cm.get_caller()

        assert caller.h5_file_path is None
        assert caller.node_name is None
        assert caller.caller_name == 'FakeModuleSaver'
        assert cm._h5saver is None

    def test_closed_h5_file_gives_path_but_no_node(self, qtbot):
        # e.g. the saver left on a detector after a scan whose file has been closed
        cm = ControlModule()
        cm._module_and_data_saver = FakeModuleSaver(
            h5saver=FakeH5Saver(is_open=False), module_group=ClosedGroup())

        caller = cm.get_caller()

        assert caller.h5_file_path == '/tmp/data/Data_20260101.h5'
        assert caller.node_name is None
        assert cm._h5saver is None

    def test_derives_caller_from_module_and_data_saver(self, qtbot):
        cm = ControlModule()
        cm._module_and_data_saver = FakeModuleSaver(
            h5saver=FakeH5Saver(), module_group=FakeGroup('/RawData/Detector000'))

        caller = cm.get_caller()

        assert caller == CallerInfo(h5_file_path='/tmp/data/Data_20260101.h5',
                                    node_name='Detector000', caller_name='FakeModuleSaver')

    def test_no_module_group_leaves_node_name_none(self, qtbot):
        cm = ControlModule()
        cm._module_and_data_saver = FakeModuleSaver(h5saver=FakeH5Saver(), module_group=None)

        caller = cm.get_caller()

        assert caller.node_name is None
        assert caller.h5_file_path == '/tmp/data/Data_20260101.h5'


class TestPluginBaseGetCaller:
    def test_none_when_parent_has_no_caller_attribute(self, qtbot):
        plugin = PluginBase(parent=None)
        assert plugin.get_caller() is None

    def test_reads_caller_set_on_parent_worker(self, qtbot):
        worker = HardwareWorkerBase(title='test', plugin_name='Mock')
        plugin = PluginBase(parent=worker)
        assert plugin.get_caller() is None

        caller = CallerInfo(h5_file_path='/tmp/a.h5', node_name='Scan001')
        worker.set_caller(caller)
        assert plugin.get_caller() is caller


class TestHardwareWorkerBaseCaller:
    def test_initial_caller_is_none(self, qtbot):
        worker = HardwareWorkerBase(title='test', plugin_name='Mock')
        assert worker._caller is None

    def test_set_caller_updates_state(self, qtbot):
        worker = HardwareWorkerBase(title='test', plugin_name='Mock')
        caller = CallerInfo(h5_file_path='/tmp/a.h5')
        worker.set_caller(caller)
        assert worker._caller is caller
