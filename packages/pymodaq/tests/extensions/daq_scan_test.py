# -*- coding: utf-8 -*-
"""Tests for pymodaq.extensions.scan.daq_scan"""
from unittest.mock import Mock
from dataclasses import dataclass
import pytest
from qtpy import QtCore

from pymodaq_gui.parameter import Parameter

from pymodaq.extensions.scan.daq_scan import DAQScan, DAQScanAcquisition
from pymodaq.utils.managers.modules import ModulesManager
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
