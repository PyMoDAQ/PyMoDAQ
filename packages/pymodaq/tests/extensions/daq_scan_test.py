# -*- coding: utf-8 -*-
"""Tests for pymodaq.extensions.scan.daq_scan"""
from unittest.mock import Mock

import pytest

from pymodaq_gui.parameter import Parameter

from pymodaq.extensions.scan.daq_scan import DAQScan, DAQScanAcquisition
from pymodaq.utils.managers.modules import ModulesManager


@pytest.fixture
def scan_settings():
    return Parameter.create(name='settings', type='group', children=DAQScan.params)


@pytest.fixture
def scan_acquisition(qtbot, scan_settings):
    scanner = Mock()
    scanner.get_scan_shape.return_value = []
    modules_manager = ModulesManager()

    return DAQScanAcquisition(scan_settings=scan_settings, scanner=scanner,
                               modules_manager=modules_manager)


class TestTimeout:

    def test_stops_scan_when_stop_on_timeout_enabled(self, qtbot, scan_acquisition, scan_settings):
        scan_settings.child('scan_options', 'stop_on_timeout').setValue(True)

        with qtbot.waitSignal(scan_acquisition.status_sig, timeout=500):
            scan_acquisition.timeout(['Det1'])

        assert scan_acquisition.timeout_scan_flag

    def test_does_not_stop_scan_when_stop_on_timeout_disabled(self, qtbot, scan_acquisition,
                                                                scan_settings):
        scan_settings.child('scan_options', 'stop_on_timeout').setValue(False)

        with qtbot.waitSignal(scan_acquisition.status_sig, timeout=500):
            scan_acquisition.timeout(['Det1'])

        assert not scan_acquisition.timeout_scan_flag

    def test_message_includes_missing_modules(self, qtbot, scan_acquisition):
        messages = []
        scan_acquisition.status_sig.connect(lambda cmd: messages.append(cmd))

        scan_acquisition.timeout(['Det1', 'X_axis'])

        timeout_cmds = [cmd for cmd in messages if cmd.command == 'Timeout']
        assert len(timeout_cmds) == 1
        assert 'Det1' in timeout_cmds[0].attribute
        assert 'X_axis' in timeout_cmds[0].attribute

    def test_message_without_missing_modules(self, qtbot, scan_acquisition):
        messages = []
        scan_acquisition.status_sig.connect(lambda cmd: messages.append(cmd))

        scan_acquisition.timeout()

        timeout_cmds = [cmd for cmd in messages if cmd.command == 'Timeout']
        assert len(timeout_cmds) == 1
        assert timeout_cmds[0].attribute == 'Timeout during acquisition'
