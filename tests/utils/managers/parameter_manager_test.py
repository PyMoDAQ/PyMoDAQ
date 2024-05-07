1# -*- coding: utf-8 -*-
"""
Created the 07/11/2023

@author: Sebastien Weber
"""
from collections import OrderedDict
import pytest
from qtpy import QtWidgets

from pymodaq.examples.parameter_ex import ParameterEx, Parameter
from pymodaq.utils.parameter.utils import (iter_children_params, compareParameters,
                                           compareStructureParameter,
                                           compareValuesParameter)
from pymodaq.utils.gui_utils.widgets.table import TableModel
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
        {'title': 'Linear Slide float', 'name': 'linearslidefloat', 'type': 'slide', 'value': 50,
         'default': 50, 'min': 0,
         'max': 123, 'subtype': 'linear'},
        {'title': 'Log Slide float', 'name': 'logslidefloat', 'type': 'slide', 'value': 50,
         'default': 50, 'min': 1e-5,
         'max': 1e5, 'subtype': 'log'},
    ]},


def test_parameter_manager(qtbot):

    param_manager = RealParameterManager()
    param_manager.settings_tree.show()

    assert hasattr(param_manager.settings_tree, 'header')
    assert hasattr(param_manager.settings_tree, 'setMinimumHeight')
    assert hasattr(param_manager.settings_tree, 'listAllItems')


def test_save(qtbot, tmp_path):
    ptree = ParameterEx()
    ptree.settings_tree.show()
    qtbot.addWidget(ptree.settings_tree)

    file_path = tmp_path.joinpath('settings.xml')
    ptree.save_settings_slot(file_path)


def test_load(qtbot, tmp_path):
    ptree = ParameterEx()
    ptree.settings_tree.show()
    qtbot.addWidget(ptree.settings_tree)

    file_path = tmp_path.joinpath('settings.xml')
    ptree.save_settings_slot(file_path)

    parameter_copy = Parameter.create(name='settings', type='group', children=ParameterEx.params)
    compareValuesParameter(ptree.settings, parameter_copy)

    parameters = iter_children_params(ptree.settings, childlist=[])
    parameters_copy = iter_children_params(parameter_copy, childlist=[])

    for parameter in parameters:
        if not parameter.hasChildren() and 'group' not in parameter.opts['type']:
            default_parameter = Parameter.create(name='settings', type=parameter.opts['type'])
            if not 'table' in parameter.opts['type']:
                item = default_parameter.makeTreeItem(0)
                if hasattr(item, 'widget'):
                    parameter.setValue(item.widget.value())
            elif 'tablewidget' == parameter.opts['type']:
                parameter.setValue(OrderedDict(key1='data10', key2='25'))
            elif 'tabular_table' == parameter.opts['type']:
                parameter.setValue(TableModel([[0.5, 0.2, 0.6]], ['value20', 'val2', '555']))

    assert not compareValuesParameter(ptree.settings, parameter_copy)
    assert compareStructureParameter(ptree.settings, parameter_copy)

    ptree.update_settings_slot(file_path)
    parameters = iter_children_params(ptree.settings, childlist=[])

    for parameter, pcopy in zip(parameters, parameters_copy):
        if parameter.value() != pcopy.value():
            print(parameter)

    assert compareValuesParameter(ptree.settings, parameter_copy)
    assert compareStructureParameter(ptree.settings, parameter_copy)
