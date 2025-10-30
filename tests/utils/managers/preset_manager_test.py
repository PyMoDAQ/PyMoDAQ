1# -*- coding: utf-8 -*-
"""
Created the 07/11/2023

@author: Sebastien Weber
"""
from collections import OrderedDict
import pytest
from qtpy import QtWidgets
from pymodaq.utils.managers import PresetManager



@pytest.fixture
def ini_qt_widget(init_qt):
    qtbot = init_qt
    widget = QtWidgets.QWidget()
    qtbot.addWidget(widget)
    widget.show()
    yield qtbot, widget
    widget.close()



def test_preset_manager(qtbot):
    """
    Testing the validity of the PresetManager object initialization.
    Qt not tested
    :param qtbot:
    :return:
    """
    preset_manager = PresetManager()
    assert preset_manager
