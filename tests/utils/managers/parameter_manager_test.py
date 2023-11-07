# -*- coding: utf-8 -*-
"""
Created the 07/11/2023

@author: Sebastien Weber
"""
from qtpy import QtWidgets

import pytest
import pytestqt


from pymodaq.utils.managers.parameter_manager import ParameterManager


@pytest.fixture
def ini_qt_widget(init_qt):
    qtbot = init_qt
    widget = QtWidgets.QWidget()
    qtbot.addWidget(widget)
    widget.show()
    yield qtbot, widget
    widget.close()


class RealParameterManager(ParameterManager):
    params = {'title': 'Numbers:', 'name': 'numbers', 'type': 'group', 'children': [
        {'title': 'Standard float', 'name': 'afloat', 'type': 'float', 'value': 20., 'min': 1.,
         'tip': 'displays this text as a tooltip'},
        {'title': 'Linear Slide float', 'name': 'linearslidefloat', 'type': 'slide', 'value': 50, 'default': 50,
         'min': 0,
         'max': 123, 'subtype': 'linear'},
        {'title': 'Log Slide float', 'name': 'logslidefloat', 'type': 'slide', 'value': 50, 'default': 50,
         'min': 1e-5,
         'max': 1e5, 'subtype': 'log'},
    ]},


def test_parameter_manager(qtbot):

    param_manager = RealParameterManager()
    param_manager.settings_tree.show()

    assert hasattr(param_manager.settings_tree, 'header')
    assert hasattr(param_manager.settings_tree, 'setMinimumHeight')



