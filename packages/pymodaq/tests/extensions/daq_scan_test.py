# -*- coding: utf-8 -*-
"""Tests for pymodaq.extensions.scan.daq_scan"""
from unittest.mock import Mock

import numpy as np
from dataclasses import dataclass
import pytest
from qtpy import QtCore

from pymodaq_data.data import Axis, DataRaw, DataToExport
from pymodaq_gui.parameter import Parameter

from pymodaq.extensions.scan.daq_scan import DAQScan, DAQScanAcquisition
from pymodaq.extensions.scan.daq_scan import DAQScanCaller
from pymodaq.utils.managers.modules import ModulesManager
from pymodaq.utils.caller import CallerInfo
from pymodaq_utils.utils import ThreadCommand


@pytest.fixture
def scan_settings():
    return Parameter.create(name='settings', type='group', children=DAQScan.params)


@pytest.fixture
def scan_acquisition(qtbot, scan_settings, monkeypatch):
    scanner = Mock()
    scanner.get_scan_shape.return_value = []
    modules_manager = ModulesManager()
    status_manager = Mock()
    status_manager.set_permanent_status.return_value = None

    class DAQScan(QtCore.QObject):
        status_sig = QtCore.Signal(ThreadCommand)


        def __init__(self, settings: Parameter,
                     scanner: Mock,
                     modules_manager: ModulesManager,
                     module_and_data_saver: Mock = None):
            super().__init__()
            self.settings = settings
            self.scanner = scanner
            self.modules_manager = modules_manager
            self.module_and_data_saver = module_and_data_saver
            self.status_manager = status_manager
            self.has_action = Mock(return_value=False)

        def set_action_checked(self, action: str, status: bool):
            pass

        def enable_workflow_actions(self, *args, **kwargs):
            pass

    def terminate_workers(obj):
        return



    scan = DAQScan(scan_settings, scanner, modules_manager)
    monkeypatch.setattr(DAQScanAcquisition, "terminate_workers", terminate_workers)

    return DAQScanAcquisition(daq_scan=scan)


@pytest.mark.skip
class TestTimeout:
    def test_stops_scan_when_stop_on_timeout_enabled(self, qtbot, scan_acquisition, scan_settings):
        scan_settings.child('scan_options', 'stop_on_timeout').setValue(True)
        scan_acquisition._running = True
        scan_acquisition.init_things()
        scan_acquisition.scan_step_failed_signal.disconnect(scan_acquisition._on_scan_step_failed)

        with qtbot.waitSignal(scan_acquisition._app.status_sig, timeout=500):
            scan_acquisition.timeout(['Det1'])

        assert scan_acquisition.timeout_scan_flag
        assert not scan_acquisition.is_running

    def test_does_not_stop_scan_when_stop_on_timeout_disabled(self, qtbot, scan_acquisition,
                                                                scan_settings):
        scan_settings.child('scan_options', 'stop_on_timeout').setValue(False)
        scan_acquisition._running = True
        scan_acquisition.init_things()
        scan_acquisition.scan_step_failed_signal.disconnect(scan_acquisition._on_scan_step_failed)

        with qtbot.waitSignal(scan_acquisition._app.status_sig, timeout=500):
            scan_acquisition.timeout(['Det1'])

        assert scan_acquisition.timeout_scan_flag
        assert scan_acquisition.is_running

    def test_message_includes_missing_modules(self, qtbot, scan_acquisition):
        messages = []
        scan_acquisition.init_things()
        def append_msg(msg: str):
            messages.append(msg)

        scan_acquisition._app.status_sig.connect(append_msg)

        with qtbot.waitSignal(scan_acquisition._app.status_sig, timeout=500):
            scan_acquisition.timeout(['Det1', 'X_axis'])

        timeout_cmds = [cmd for cmd in messages if cmd.command == 'Timeout']
        assert len(timeout_cmds) == 1
        assert 'Det1' in timeout_cmds[0].attribute
        assert 'X_axis' in timeout_cmds[0].attribute

    def test_message_without_missing_modules(self, qtbot, scan_acquisition):
        messages = []
        scan_acquisition.init_things()
        def append_msg(msg: str):
            messages.append(msg)

        scan_acquisition._app.status_sig.connect(append_msg)

        with qtbot.waitSignal(scan_acquisition._app.status_sig, timeout=500):
            scan_acquisition.timeout()

        timeout_cmds = [cmd for cmd in messages if cmd.command == 'Timeout']
        assert len(timeout_cmds) == 1
        assert timeout_cmds[0].attribute == 'Timeout during acquisition'


class TestNaverage:
    def test_naverage_is_read_when_the_scan_starts(self, scan_acquisition, scan_settings):
        """The number of averages set after the creation of the acquisition must be used by the scan"""
        scan_settings.child('scan_options', 'scan_average').setValue(3)

        scan_acquisition.init_things()

        assert scan_acquisition.Naverage == 3

    def test_indexes_and_nav_axes_include_the_average(self, scan_acquisition, scan_settings):
        scan_settings.child('scan_options', 'scan_average').setValue(3)
        for name in ('plot_0d', 'plot_1d'):
            scan_settings.child('plot_options', name).setValue(dict(all_items=[], selected=[]))
        scan_acquisition.init_things()
        scan_acquisition.saver_worker = Mock()
        scan_acquisition.thread_manager = Mock()
        scan_acquisition.thread_manager.n_jobs = {'SaverWorker': 0}
        scan_acquisition._on_scan_step_done = Mock()

        scanner = scan_acquisition.scanner
        scanner.get_indexes_from_scan_index.return_value = (0,)
        scanner.get_nav_axes.return_value = [Axis('x', 'm', data=np.arange(4.), index=0)]
        scanner.scanner.do_process_data = False

        scan_acquisition._ind_average = 1
        scan_acquisition._ind_scan = 0
        dte = DataToExport('dte', data=[DataRaw('det', data=[np.zeros((1,))], origin='Det0D')])

        scan_acquisition.det_done(dte)

        bundle = scan_acquisition.saver_worker.data_to_save_signal.emit.call_args[0][0]
        assert bundle.indexes == [1, 0]  # [average index, scan index]
        nav_axes = scan_acquisition.saver_worker.nav_axes_signal.emit.call_args[0][0]
        assert {axis.label: axis.index for axis in nav_axes} == {'Average': 0, 'x': 1}


class TestDAQScanCaller:
    def test_is_a_caller_base(self):
        assert isinstance(DAQScanCaller(), CallerInfo)

    def test_defaults(self):
        caller = DAQScanCaller()
        assert caller.caller_name == 'DAQScan'
        assert caller.caller_type == 'DAQScanCaller'
        assert caller.ind_scan == 0
        assert caller.ind_average == 0
        assert caller.h5_file_path is None
        assert caller.node_name is None

    def test_explicit_values(self):
        caller = DAQScanCaller(ind_scan=3, ind_average=1, node_name='Scan001',
                               h5_file_path='/tmp/data.h5')
        assert caller.ind_scan == 3
        assert caller.ind_average == 1
        assert caller.node_name == 'Scan001'
        assert caller.h5_file_path == '/tmp/data.h5'
        assert caller.caller_name == 'DAQScan'
        assert caller.caller_type == 'DAQScanCaller'
