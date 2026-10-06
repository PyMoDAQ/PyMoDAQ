# -*- coding: utf-8 -*-
"""Tests for pymodaq.extensions.scan.manager.scan_manager"""
from unittest import mock

import numpy as np
import qt_themes
from pytest import fixture
from qtpy import QtWidgets

from pymodaq_data.data import DataRaw, DataToExport
from pymodaq_utils.config import GlobalConfig

from pymodaq.dashboard import create_load_dashboard
from pymodaq.extensions.scan.daq_scan import DAQScan
from pymodaq.utils.gui_utils.loader_utils import create_extension

config = GlobalConfig()


@fixture
def scan(qtbot):
    qt_themes.set_theme(theme=config('gui', 'style', 'theme')[0],
                        style=config('gui', 'style', 'style')[0])
    shared_ui, dashboard = create_load_dashboard()
    qtbot.addWidget(shared_ui.parent)
    qtbot.addWidget(dashboard.tree)
    win_ext, daq_scan = create_extension(dashboard, DAQScan)
    yield daq_scan
    daq_scan.quit_fun()
    QtWidgets.QApplication.processEvents()
    dashboard.quit_fun()


class TestScanManager:
    def test_settings_structure(self, scan):
        settings = scan.scan_manager.settings

        assert settings.child('daq_scan', 'plot_options', 'plot_0d') is not None
        assert settings.child('daq_scan', 'plot_options', 'plot_1d') is not None
        assert settings.child('h5saver') is not None

    def test_probe_data(self, scan):
        scan_manager = scan.scan_manager
        dte = DataToExport('probed', data=[
            DataRaw('scalar', data=[np.zeros((1,))], origin='Det0D'),
            DataRaw('waveform', data=[np.zeros((5,))], origin='Det1D')])

        with mock.patch.object(scan_manager.modules_manager, 'connect_detectors'), \
                mock.patch.object(scan_manager.modules_manager, 'grab_data', return_value=dte):
            scan_manager.probe_data()

        plot_0d = scan_manager.settings['daq_scan', 'plot_options', 'plot_0d']
        plot_1d = scan_manager.settings['daq_scan', 'plot_options', 'plot_1d']
        assert plot_0d['all_items'] == ['Det0D/scalar']
        assert plot_1d['all_items'] == ['Det1D/waveform']
        assert plot_0d['selected'] == []
        assert plot_1d['selected'] == []
