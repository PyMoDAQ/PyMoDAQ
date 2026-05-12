# -*- coding: utf-8 -*-
"""
Created the 29/08/2023

@author: Sebastien Weber
"""
import pytest
import numpy as np

from qtpy import QtWidgets

from pymodaq_gui.examples.parameter_ex import ParameterEx
from pymodaq_utils.utils import find_objects_in_list_from_attr_name_val
from pymodaq_gui.parameter import Parameter, ParameterTree
from pymodaq_gui.parameter import utils as putils
from pymodaq_gui.parameter import ioxml
from pathlib import Path



axes_names = {'Axis 1': 0, 'Axis 2': 1, 'Axis 3': 2}

params = [{'title': 'Axes', 'name': 'axes', 'type': 'list', 'limits': axes_names}]

settings = Parameter.create(name='settings', type='group', children=params)
# experiment = PresentManager()

string = ioxml.parameter_to_xml_string(settings.child('axes'))

ioxml.XML_string_to_pobject(string)
list_limits = ['DAQ0D', 'DAQ1D', 'DAQ2D', 'DAQND']
dict_limits = {'a_nan': np.nan, 'an_int': 21, 'a_str': 'astr'}


@pytest.fixture
def ini_parameter(qtbot):

    params = [{'name': 'list_param', 'type': 'list', 'limits': list_limits},
              {'name': 'dict_param', 'type': 'list', 'limits': dict_limits},
              ]

    settings = Parameter.create(name='settings', children=params)
    tree = ParameterTree()
    qtbot.addWidget(tree)
    tree.setParameters(settings, showTop=False)
    yield settings, tree
    tree.close()
    
    
class TestListParameter:

    def test_value(self, ini_parameter):
        settings, tree = ini_parameter

        assert settings['list_param'] == 'DAQ0D'
        assert settings['dict_param'] is np.nan

        list_item, _ = find_objects_in_list_from_attr_name_val(tree.listAllItems(),
                                                               'param', settings.child('list_param'))
        dict_item, _ = find_objects_in_list_from_attr_name_val(tree.listAllItems(), 'param',
                                                               settings.child('dict_param'))
        list_widget: QtWidgets.QComboBox = list_item.widget.combo
        dict_widget: QtWidgets.QComboBox = dict_item.widget.combo

        list_item.setValue('DAQND')
        dict_item.setValue('astr')

        assert settings['list_param'] == 'DAQND'
        assert settings['dict_param'] == 'astr'

        list_item.setValue('DAQ4D')  # not in limits so should be set to the first element of the underlying combobox
        dict_item.setValue('DAQ1D')  # not in limits (because should be values of the dict, not keys) so should be
        # set to the first element of the underlying combobox

        assert settings['list_param'] == list_widget.itemText(0)
        try:
            assert settings['dict_param'] == dict_limits[dict_widget.itemText(0)]
        except AssertionError:
            assert settings['dict_param'] is dict_limits[dict_widget.itemText(0)]

    def test_save_xml_list(self, ini_parameter):
        settings, tree = ini_parameter
        xml_string = ioxml.parameter_to_xml_string(settings.child('list_param'))

        param_back = ioxml.XML_string_to_pobject(xml_string).child('list_param')
        assert param_back.name() == settings.child('list_param').name()
        assert param_back.title() == settings.child('list_param').title()
        assert param_back.value() == settings.child('list_param').value()
        assert param_back.readonly() == settings.child('list_param').readonly()
        assert param_back.opts['limits'] == settings.child('list_param').opts['limits']
        assert param_back.opts['removable'] == settings.child('list_param').opts['removable']

    def test_save_xml_dict(self, ini_parameter):
        settings, tree = ini_parameter
        for value_key in dict_limits:
            settings.child('dict_param').setValue(dict_limits[value_key])
            xml_string = ioxml.parameter_to_xml_string(settings.child('dict_param'))

            param_back = ioxml.XML_string_to_pobject(xml_string).child('dict_param')
            assert param_back.name() == settings.child('dict_param').name()
            assert param_back.title() == settings.child('dict_param').title()
            try:
                assert param_back.value() == settings.child('dict_param').value()
            except AssertionError:
                assert param_back.value() is settings.child('dict_param').value()
            assert param_back.readonly() == settings.child('dict_param').readonly()
            assert param_back.opts['limits'] == settings.child('dict_param').opts['limits']
            assert param_back.opts['removable'] == settings.child('dict_param').opts['removable']


class TestXMLbackForth():

    params = ParameterEx.params
    settings = Parameter.create(name='settings', type='group', children=params)

    def test_save_load_xml(self):

        param_back = ioxml.XML_string_to_pobject(ioxml.parameter_to_xml_string(settings))
        children_list_in = putils.iter_children_params(settings)
        children_list_back = putils.iter_children_params(param_back)
        for child, child_back in zip(children_list_in,children_list_back):
            assert child_back.name() == child.name()
            assert child_back.title() == child.title()
            if 'value' in child_back.opts:
                assert child_back.value() == child.value()
            assert child_back.readonly() == child.readonly()
            if 'limits' in child_back.opts:
                assert child_back.opts['limits'] == child.opts['limits']
            assert child_back.opts['removable'] == child.opts['removable']

    def test_load_save_overwrite_xml_file(self, tmp_path):
        """
        Testing to load default experiment saving it under a name,
        raising an exception when trying to overwrite then forcing overwrite
        :return:
        """
        defaultparameter = Parameter.create(title='Experiment', name='Experiment', type='group',
                                            children=ioxml.XML_file_to_parameter(
                                                Path(__file__).resolve().parent.parent.joinpath(
                                                    'data/preset_default.xml')))
        saveto = tmp_path.joinpath('impossiblenamedonotuse')
        ioxml.parameter_to_xml_file(defaultparameter,
                                    saveto)
        assert saveto.with_suffix(".xml").is_file()
        origin_modification_time = saveto.with_suffix(".xml").stat().st_mtime_ns
        with pytest.raises(FileExistsError):
            ioxml.parameter_to_xml_file(defaultparameter, saveto, overwrite=False)

        assert saveto.with_suffix(".xml").stat().st_mtime_ns == origin_modification_time

        ioxml.parameter_to_xml_file(defaultparameter,
                                    saveto,
                                    overwrite=True)
        assert saveto.with_suffix(".xml").stat().st_mtime_ns >= origin_modification_time



