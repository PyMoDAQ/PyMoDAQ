# -*- coding: utf-8 -*-
"""
Created the 29/08/2023

@author: Sebastien Weber
"""

import numpy as np
import pytest

from qtpy import QtWidgets

from pymodaq.examples.parameter_ex import ParameterEx
from pymodaq.utils.daq_utils import find_objects_in_list_from_attr_name_val
from pymodaq.utils.parameter import Parameter, ParameterTree
from pymodaq.utils.parameter import utils as putils
from pymodaq.utils.parameter import ioxml
from unittest import mock


axes_names = {'Axis 1': 0, 'Axis 2': 1, 'Axis 3': 2}

params = [{'title': 'Axes', 'name': 'axes', 'type': 'list', 'limits': axes_names}]

settings = Parameter.create(name='settings', type='group', children=params)


string = ioxml.parameter_to_xml_string(settings.child('axes'))

ioxml.XML_string_to_pobject(string)


class TestListParameter:

    list_limits = ['DAQ0D', 'DAQ1D', 'DAQ2D', 'DAQND']
    dict_limits = {'DAQ0D': 0, 'DAQ1D': 1, 'DAQ2D': 2, 'DAQND': 3}

    params = [{'name': 'list_param', 'type': 'list', 'limits': list_limits},
              {'name': 'dict_param', 'type': 'list', 'limits': dict_limits},
              ]

    settings = Parameter.create(name='settings', children=params)

    def test_value(self, qtbot):
        tree = ParameterTree()
        tree.setParameters(self.settings, showTop=False)

        assert self.settings['list_param'] == 'DAQ0D'
        assert self.settings['dict_param'] == 0

        list_item, _ = find_objects_in_list_from_attr_name_val(tree.listAllItems(),
                                                               'param', self.settings.child('list_param'))
        dict_item, _ = find_objects_in_list_from_attr_name_val(tree.listAllItems(), 'param',
                                                               self.settings.child('dict_param'))
        list_widget: QtWidgets.QComboBox = list_item.widget.combo
        dict_widget: QtWidgets.QComboBox = dict_item.widget.combo

        list_item.setValue('DAQND')
        dict_item.setValue(3)

        assert self.settings['list_param'] == 'DAQND'
        assert self.settings['dict_param'] == 3

        list_item.setValue('DAQ4D')  # not in limits so should be set to the first element of the underlying combobox
        dict_item.setValue('DAQ1D')  # not in limits (because should be values of the dict, not keys) so should be
        # set to the first element of the underlying combobox

        assert self.settings['list_param'] == list_widget.itemText(0)
        assert self.settings['dict_param'] == self.dict_limits[dict_widget.itemText(0)]

    def test_save_xml_list(self):
        xml_string = ioxml.parameter_to_xml_string(self.settings.child('list_param'))

        param_back = ioxml.XML_string_to_pobject(xml_string).child('list_param')
        assert param_back.name() == self.settings.child('list_param').name()
        assert param_back.title() == self.settings.child('list_param').title()
        assert param_back.value() == self.settings.child('list_param').value()
        assert param_back.readonly() == self.settings.child('list_param').readonly()
        assert param_back.opts['limits'] == self.settings.child('list_param').opts['limits']
        assert param_back.opts['removable'] == self.settings.child('list_param').opts['removable']

    def test_save_xml_dict(self):
        xml_string = ioxml.parameter_to_xml_string(self.settings.child('dict_param'))

        param_back = ioxml.XML_string_to_pobject(xml_string).child('dict_param')
        assert param_back.name() == self.settings.child('dict_param').name()
        assert param_back.title() == self.settings.child('dict_param').title()
        assert param_back.value() == self.settings.child('dict_param').value()
        assert param_back.readonly() == self.settings.child('dict_param').readonly()
        assert param_back.opts['limits'] == self.settings.child('dict_param').opts['limits']
        assert param_back.opts['removable'] == self.settings.child('dict_param').opts['removable']


class TestXMLbackForth:

    params = ParameterEx.params
    settings = Parameter.create(name='settings', type='group', children=params)

    def test_save_load_xml(self):

        param_back = ioxml.XML_string_to_pobject(ioxml.parameter_to_xml_string(self.settings))

        for child, child_back in zip(putils.iter_children_params(self.settings),
                                     putils.iter_children_params(param_back)):
            assert child_back.name() == child.name()
            assert child_back.title() == child.title()
            assert child_back.value() == child.value()
            assert child_back.readonly() == child.readonly()
            if 'limits' in child_back.opts:
                assert child_back.opts['limits'] == child.opts['limits']
            assert child_back.opts['removable'] == child.opts['removable']



