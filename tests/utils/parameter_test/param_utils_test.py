# -*- coding: utf-8 -*-
"""
Created the 28/10/2022

@author: Sebastien Weber
"""
import numpy as np
import pytest
from qtpy import QtWidgets
from collections import OrderedDict
from pymodaq.utils.parameter import Parameter, ParameterTree
from pymodaq.utils.parameter import utils as putils
from pymodaq.utils.parameter import ioxml
from unittest import mock
from pymodaq.utils.daq_utils import find_objects_in_list_from_attr_name_val

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
params1 = [
    {'title': 'Numbers:', 'name': 'numbers', 'type': 'group', 'children': [
        {'title': 'Standard float', 'name': 'afloat', 'type': 'float', 'value': 20., 'min': 1.,
            'tip': 'displays this text as a tooltip','children':
                [{'title': 'Standard int:', 'name': 'aint', 'type': 'int', 'value': 20,}]},
        ]},
]
# No min for afloat ==) False, True, True
params2 = [
    {'title': 'Numbers:', 'name': 'numbers', 'type': 'group', 'children': [
        {'title': 'Standard float', 'name': 'afloat', 'type': 'float', 'value': 20.,
            'tip': 'displays this text as a tooltip','children':
                [{'title': 'Standard int:', 'name': 'aint', 'type': 'int', 'value': 20,}]},
    ]},
]
# No children in afloat ==) False, False, False
params3 = [
    {'title': 'Numbers:', 'name': 'numbers', 'type': 'group', 'children': [
        {'title': 'Standard float', 'name': 'afloat', 'type': 'float', 'value': 20., 'min': 1.,
            'tip': 'displays this text as a tooltip','children':
                []},
    ]},
]
# Different value in afloat ==) False, False, True
params4 = [
    {'title': 'Numbers:', 'name': 'numbers', 'type': 'group', 'children': [
        {'title': 'Standard float', 'name': 'afloat', 'type': 'float', 'value': 10., 'min': 1.,
            'tip': 'displays this text as a tooltip','children':
                [{'title': 'Standard int:', 'name': 'aint', 'type': 'int', 'value': 20,}]},
    ]},
]    
P1 = Parameter(name='settings1', type='group', children=params1)
P2 = Parameter(name='settings2', type='group', children=params2)
P3 = Parameter(name='settings3', type='group', children=params3)
P4 = Parameter(name='settings4', type='group', children=params4)

def test_get_param_path():
    settings = Parameter.create(name='settings', type='group', children=params)

    assert putils.get_param_path(settings) == ['settings']
    path = putils.get_param_path(settings.child('main_settings', 'DAQ_type'))
    assert path == ['settings', 'main_settings', 'DAQ_type']


def test_get_param_from_name():
    settings = Parameter.create(name='settings', type='group', children=params)
    assert putils.get_param_from_name(settings, 'DAQ_type') is settings.child('main_settings', 'DAQ_type')
    assert putils.get_param_from_name(settings, 'noname') is None


def test_is_name_in_dict():
    dict = {'name': 'test', 'parameter': 'gaussian', 'value': 5}
    assert putils.is_name_in_dict(dict, 'test')
    assert not putils.is_name_in_dict(dict, 'gaussian')


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
    
def test_getOpts():
    opts = putils.getOpts(P1)
    assert [len(opts['numbers'][0])==13,
            len(opts['numbers'][1]['afloat'][0])==15,
            len(opts['numbers'][1]['afloat'][1]['aint'][0])==13]            
    
def test_getStruct():
    struc = putils.getStruct(P1)
    assert [struc['numbers'][0]==None,
            struc['numbers'][1]['afloat'][0]==None,
            struc['numbers'][1]['afloat'][1]['aint'][0]==None]                   

def test_getValues():
    val = putils.getValues(P1)
    assert [val['numbers'][0]==None,
            val['numbers'][1]['afloat'][0]==20.0,
            val['numbers'][1]['afloat'][1]['aint'][0]==20]             


def test_compareParameters():      
    assert [putils.compareParameters(param1=P1,param2=P1) == True,
            putils.compareParameters(param1=P1,param2=P2) == False,
            putils.compareParameters(param1=P1,param2=P3) == False,
            putils.compareParameters(param1=P1,param2=P4) == False]        
def test_compareStructureParameter():  
    assert [putils.compareStructureParameter(param1=P1,param2=P1) == True,
            putils.compareStructureParameter(param1=P1,param2=P2) == True,
            putils.compareStructureParameter(param1=P1,param2=P3) == False,
            putils.compareStructureParameter(param1=P1,param2=P4) == True]    

def test_compareValuesParameter():  
    assert [putils.compareValuesParameter(param1=P1,param2=P1) == True,
            putils.compareValuesParameter(param1=P1,param2=P2) == True,
            putils.compareValuesParameter(param1=P1,param2=P3) == False,
            putils.compareValuesParameter(param1=P1,param2=P4) == False]

        

    


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


def test_set_param_from_param(qtbot):
    params = [
        {'title': 'Main Settings:', 'name': 'main_settings', 'expanded': False, 'type': 'group', 'children': [
            {'title': 'DAQ type:', 'name': 'DAQ_type', 'type': 'list', 'limits': ['DAQ0D', 'DAQ1D', 'DAQ2D', 'DAQND'],
             'readonly': True},
            {'title': 'axis names:', 'name': 'axis', 'type': 'list',
             'limits': {'DAQ0D': 0, 'DAQ1D': 1, 'DAQ2D': 2, 'DAQND': 3}, 'value': 'DAQ1D',' readonly': True},
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

    tree = ParameterTree()
    tree.setParameters(settings_old, showTop=False)

    dict_item, _ = find_objects_in_list_from_attr_name_val(tree.listAllItems(), 'param',
                                                           settings_old.child('main_settings', 'axis'))
    dict_widget: QtWidgets.QComboBox = dict_item.widget.combo

    settings.child('main_settings', 'axis').setLimits({'DAQ4D': 4})
    settings.child('main_settings', 'axis').setValue(4)
    putils.set_param_from_param(param_old=settings_old, param_new=settings)

    assert settings_old.child('main_settings', 'axis').value() == 4
    assert dict_widget.currentText() == 'DAQ4D'

    settings_old.child('main_settings', 'axis').setValue(2)

    assert settings_old.child('main_settings', 'axis').value() == 2
    assert dict_widget.currentText() == 'DAQ2D'

