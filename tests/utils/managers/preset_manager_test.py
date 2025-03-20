1# -*- coding: utf-8 -*-
"""
Created the 07/11/2023

@author: Sebastien Weber
"""
from collections import OrderedDict
import pytest
from qtpy import QtWidgets

# from pymodaq.examples.parameter_ex import ParameterEx, Parameter
# from pymodaq.utils.parameter.utils import (iter_children_params, compareParameters,
#                                            compareStructureParameter,
#                                            compareValuesParameter)
# from pymodaq.utils.gui_utils.widgets.table import TableModel
# from pymodaq.utils.managers.parameter_manager import ParameterManager
# from pymodaq.utils.managers.preset_manager import PresetManager
import pymodaq.utils.managers.preset_manager as psm
import pathlib
import pymodaq.resources as rsc

import os.path as ospath
from unittest import TestCase
from pymodaq_gui.parameter.ioxml import parameter_to_xml_file


@pytest.fixture
def ini_qt_widget(init_qt):
    qtbot = init_qt
    widget = QtWidgets.QWidget()
    qtbot.addWidget(widget)
    widget.show()
    yield qtbot, widget
    widget.close()


# subtpe Testcase ?
class TestPresetManager(psm.PresetManager):
    pass


def test_preset_manager(qtbot):
    """
    Testing the validity of the PresetManager object initialization.
    Qt not tested
    :param qtbot:
    :return:
    """
    preset_manager = TestPresetManager(False)

    assert psm.preset_path.is_dir()
    assert psm.overshoot_path.is_dir()
    assert psm.layout_path.is_dir()
    # test yes/modify/cancel ?
    assert preset_manager
