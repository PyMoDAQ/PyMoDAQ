# -*- coding: utf-8 -*-
"""
Created the 28/10/2022

@author: Sebastien Weber
"""
import numpy as np
import pytest
from qtpy import QtWidgets

from pymodaq.utils.parameter import Parameter, ParameterTree
from pymodaq.utils.parameter import utils as putils
from pymodaq.utils.parameter import ioxml
from unittest import mock


def test_get_param_path():
    item1 = mock.Mock()
    item1.name.return_value = 'first'
    item1.parent.return_value = None
    item2 = mock.Mock()
    item2.name.return_value = 'second'
    item2.parent.return_value = item1
    item3 = mock.Mock()
    item3.name.return_value = 'third'
    item3.parent.return_value = item2
    item4 = mock.Mock()
    item4.name.return_value = 'fourth'
    item4.parent.return_value = item3

    path = putils.get_param_path(item4)

    assert path == ['first', 'second', 'third', 'fourth']


def test_iter_children():
    child = mock.Mock()
    child.name.side_effect = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh']
    child.type.side_effect = [[], [], [], ['group'], [], [], []]
    child.children.side_effect = [[child, child, child]]
    param = mock.Mock()
    param.children.return_value = [child, child, child, child]

    childlist = putils.iter_children(param)

    assert childlist == ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh']


def test_iter_children_params():
    child = mock.Mock()
    child.type.side_effect = [[], [], [], ['group'], [], [], []]
    child.children.side_effect = [[child, child, child]]
    param = mock.Mock()
    param.children.return_value = [child, child, child, child]

    childlist = putils.iter_children_params(param)

    assert len(childlist) == 7


def test_get_param_from_name():
    child = mock.Mock()
    child.name.side_effect = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh']
    child.type.side_effect = [[], [], [], ['group'], [], [], []]
    child.children.side_effect = [[child, child, child]]
    param = mock.Mock()
    param.children.return_value = [child, child, child, child]

    child = putils.get_param_from_name(param, 'sixth')

    assert child.name() == 'seventh'


def test_is_name_in_dict():
    dict = {'name': 'test', 'parameter': 'gaussian', 'value': 5}
    assert putils.is_name_in_dict(dict, 'test')
    assert not putils.is_name_in_dict(dict, 'error')


def test_get_param_dict_from_name():
    parent_list = []
    for ind in range(5):
        parent_dict = {'name': ind, 'value': ind*5}
        parent_list.append(parent_dict)

    children = []
    for ind in range(5):
        parent_dict = {'name': ind*5, 'value': ind*10}
        children.append(parent_dict)

    parent_dict = {'name': 'test', 'children': children}
    parent_list.append(parent_dict)

    result = putils.get_param_dict_from_name(parent_list, 4)

    assert result['value'] == 20

    result = putils.get_param_dict_from_name(parent_list, 20, pop=True)

    assert result['value'] == 40


class TestScroll:
    def test_scroll_log(self):
        min_val = 50
        max_val = 51
        for scroll_val in range(101):
            assert putils.scroll_log(scroll_val, min_val, max_val) == \
                   pytest.approx(10 ** (scroll_val * (np.log10(max_val) - np.log10(min_val)) / 100 + np.log10(min_val)),
                                 rel=1e-4)

    def test_scroll_linear(self):
        min_val = 50
        max_val = 51
        for scroll_val in range(101):
            assert putils.scroll_linear(scroll_val, min_val, max_val) == \
                   pytest.approx(scroll_val * (max_val - min_val) / 100 + min_val)


def test_set_param_from_param():
    params = [
        {'title': 'Main Settings:', 'name': 'main_settings', 'expanded': False, 'type': 'group', 'children': [
            {'title': 'DAQ type:', 'name': 'DAQ_type', 'type': 'list', 'limits': ['DAQ0D', 'DAQ1D', 'DAQ2D', 'DAQND'],
             'readonly': True},
            {'title': 'axis names:', 'name': 'axis', 'type': 'list',
             'limits': {'DAQ0D': 0, 'DAQ1D': 1, 'DAQ2D': 2, 'DAQND': 3}, 'readonly': True},
            {'title': 'Detector type:', 'name': 'detector_type', 'type': 'str', 'value': '', 'readonly': True},
            {'title': 'Nviewers:', 'name': 'Nviewers', 'type': 'int', 'value': 1, 'min': 1, 'default': 1,
             'readonly': True},
        ]}
    ]
    settings = Parameter.create(name='settings', type='group', children=params)
    settings_old = Parameter.create(name='settings', type='group', children=params)

    settings.child('main_settings', 'detector_type').setValue('new string')
    putils.set_param_from_param(param_old=settings_old, param_new=settings)
    assert settings_old.child('main_settings', 'detector_type').value() == 'new string'

    settings = Parameter.create(name='settings', type='group', children=params)
    settings_old = Parameter.create(name='settings', type='group', children=params)

    settings.child('main_settings', 'DAQ_type').opts['limits'].append('new type')
    settings.child('main_settings', 'DAQ_type').setValue('new type')
    putils.set_param_from_param(param_old=settings_old, param_new=settings)
    assert settings_old.child('main_settings', 'DAQ_type').value() == 'new type'

    settings = Parameter.create(name='settings', type='group', children=params)
    settings_old = Parameter.create(name='settings', type='group', children=params)

    settings.child('main_settings', 'detector_type').setValue('new string')
    putils.set_param_from_param(param_old=settings_old, param_new=settings)
    assert settings_old.child('main_settings', 'detector_type').value() == 'new string'

    settings = Parameter.create(name='settings', type='group', children=params)
    settings_old = Parameter.create(name='settings', type='group', children=params)

    settings.child('main_settings', 'axis').opts['limits'].update({'DAQ4D': 4})
    settings.child('main_settings', 'axis').setValue(4)
    putils.set_param_from_param(param_old=settings_old, param_new=settings)
    assert settings_old.child('main_settings', 'axis').value() == 4


