# -*- coding: utf-8 -*-
"""
Created the 28/10/2022

@author: Sebastien Weber
"""
import numpy as np
import pytest

from pymodaq.utils.parameter import Parameter
from pymodaq.utils.parameter import utils as putils
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

    settings.child('main_settings', 'DAQ_type').opts['limits'].append('new type')
    settings.child('main_settings', 'DAQ_type').setValue('new type')
    putils.set_param_from_param(param_old=settings_old, param_new=settings)
    assert settings_old.child('main_settings', 'DAQ_type').value() == 'new type'

    settings.child('main_settings', 'detector_type').setValue('')
    putils.set_param_from_param(param_old=settings_old, param_new=settings)
    assert settings_old.child('main_settings', 'detector_type').value() == 'new string'


class TestParameterComparison:
    # Reference parameter
    params1 = [
        {'title': 'Numbers:', 'name': 'numbers', 'type': 'group', 'children': [
            {'title': 'Standard float', 'name': 'afloat', 'type': 'float', 'value': 20., 'min': 1.,
             'tip': 'displays this text as a tooltip', 'children':
                 [{'title': 'Standard int:', 'name': 'aint', 'type': 'int', 'value': 20, }]},
            {'title': 'Linear Slide float', 'name': 'linearslidefloat', 'type': 'slide', 'value': 50, 'default': 50,
             'min': 0,
             'max': 123, 'subtype': 'linear'},
            {'title': 'Log Slide float', 'name': 'logslidefloat', 'type': 'slide', 'value': 50, 'default': 50,
             'min': 1e-5,
             'max': 1e5, 'subtype': 'log'},
        ]},
    ]
    # No min max for logslidefloat in params2  ==) False, True, True
    params2 = [
        {'title': 'Numbers:', 'name': 'numbers', 'type': 'group', 'children': [
            {'title': 'Standard float', 'name': 'afloat', 'type': 'float', 'value': 20., 'min': 1.,
             'tip': 'displays this text as a tooltip', 'children':
                 [{'title': 'Standard int:', 'name': 'aint', 'type': 'int', 'value': 20, }]},
            {'title': 'Linear Slide float', 'name': 'linearslidefloat', 'type': 'slide', 'value': 50, 'default': 50,
             'min': 0,
             'max': 123, 'subtype': 'linear'},
            {'title': 'Log Slide float', 'name': 'logslidefloat', 'type': 'slide', 'value': 50, 'default': 50,
             'subtype': 'log'},
        ]},
    ]
    # No children in afloat ==) False, False, False
    params3 = [
        {'title': 'Numbers:', 'name': 'numbers', 'type': 'group', 'children': [
            {'title': 'Standard float', 'name': 'afloat', 'type': 'float', 'value': 20., 'min': 1.,
             'tip': 'displays this text as a tooltip', 'children':
                 []},
            {'title': 'Linear Slide float', 'name': 'linearslidefloat', 'type': 'slide', 'value': 50, 'default': 50,
             'min': 0,
             'max': 123, 'subtype': 'linear'},
            {'title': 'Log Slide float', 'name': 'logslidefloat', 'type': 'slide', 'value': 50, 'default': 50,
             'min': 1e-5,
             'max': 1e5, 'subtype': 'log'},
        ]},
    ]
    # Different value in afloat ==) False, False, True
    params4 = [
        {'title': 'Numbers:', 'name': 'numbers', 'type': 'group', 'children': [
            {'title': 'Standard float', 'name': 'afloat', 'type': 'float', 'value': 10., 'min': 1.,
             'tip': 'displays this text as a tooltip', 'children':
                 [{'title': 'Standard int:', 'name': 'aint', 'type': 'int', 'value': 20, }]},
            {'title': 'Linear Slide float', 'name': 'linearslidefloat', 'type': 'slide', 'value': 50, 'default': 50,
             'min': 0,
             'max': 123, 'subtype': 'linear'},
            {'title': 'Log Slide float', 'name': 'logslidefloat', 'type': 'slide', 'value': 50, 'default': 50,
             'min': 1e-5,
             'max': 1e5, 'subtype': 'log'},
        ]},
    ]

    p1 = Parameter(name='settings', type='group', children=params1)
    p2 = Parameter(name='settings', type='group', children=params2)
    p3 = Parameter(name='settings', type='group', children=params3)
    p4 = Parameter(name='settings', type='group', children=params4)

    def test_compare_parameters(self):
        compParameter = putils.compareParameters(self.p1, self.p2, opts=[])
        assert compParameter ...

    def test_compare_parameters(self):
        compValues = putils.compareValuesParameter(self.p1, self.p2)

    def test_compare_parameters(self):
        compStruct = putils.compareStructureParameter(self.p1, self.p2)
