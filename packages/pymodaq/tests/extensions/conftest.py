# -*- coding: utf-8 -*-
"""Shared fixtures of the extensions tests"""
import qt_themes
from pytest import fixture
from qtpy import QtCore, QtWidgets

from pymodaq_utils.config import GlobalConfig

from pymodaq.dashboard import create_load_dashboard
from pymodaq.extensions.scan.daq_scan import DAQScan
from pymodaq.utils.gui_utils.loader_utils import create_extension

config = GlobalConfig()


@fixture
def scan(qtbot):
    """A DAQScan extension created on an empty Dashboard"""
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
    # the windows are not deleted by the quit functions: left alive (tens of thousands of widgets with the
    # parameter trees), they slow down the event loop of every test that runs afterwards
    for widget in (win_ext.mainwindow, shared_ui.parent, dashboard.tree):
        widget.close()
        widget.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    QtWidgets.QApplication.processEvents()
