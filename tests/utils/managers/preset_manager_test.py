# -*- coding: utf-8 -*-
"""
Created the 07/11/2023

@author: Sebastien Weber
"""
from typing import Any
from collections import OrderedDict
import pytest
from pyqtgraph.examples.glow import children

from qtpy import QtWidgets
from pymodaq.utils.managers import PresetManager
from pymodaq_gui.parameter import Parameter
from pymodaq_gui.parameter.utils import compareParameters
from pymodaq_gui.parameter.ioxml import XML_file_to_parameter

@pytest.fixture
def init_qt(qtbot):
    return qtbot


@pytest.fixture
def ini_preset(init_qt):

    qtbot = init_qt

    external_ui = QtWidgets.QMainWindow()
    toolbar = QtWidgets.QToolBar()
    menu = QtWidgets.QMenu('Preset Manager Menu')
    external_ui.addToolBar(toolbar)
    external_ui.menuBar().addMenu(menu)

    preset_manager = PresetManager(menu=menu, toolbar=toolbar)
    preset_manager.update_entry_base()
    qtbot.addWidget(preset_manager.mainwindow)
    preset_manager.mainwindow.show()
    qtbot.addWidget(external_ui)

    yield preset_manager, qtbot

    preset_manager.mainwindow.close()
    external_ui.close()


class TestPresetManager:

    def test_ini(self, ini_preset):
        """
        """
        preset_manager, qtbot = ini_preset

        assert preset_manager.entry_type == 'preset'
        assert preset_manager.entry_extension == '.xml'

    def test_default(self, ini_preset):
        """
        """
        preset_manager, qtbot = ini_preset
        preset_manager.entry = 'default'

        path = preset_manager.get_entry_folder().joinpath('default.xml')
        param_list = XML_file_to_parameter(path)
        pobject = Parameter.create(name='settings', type='group',
                                   children=param_list)
        assert compareParameters(pobject, preset_manager.settings)

    def test_copy(self, ini_preset):
        preset_manager, qtbot = ini_preset
        preset_manager.entry = 'default'

        default_state = preset_manager.settings.saveState()


        copy_name = 'acopy'

        preset_manager.copy_entry('acopy', bypass_dialog=True)

        assert copy_name == preset_manager.entry
        assert copy_name in preset_manager.list_managed_entries()

        copy_state = preset_manager.settings.saveState()

        assert default_state == copy_state

        assert copy_name in [
            preset_manager.action_manager.get_action_list().itemText(ind) for ind in
            range(preset_manager.action_manager.get_action_list().count())]

    def test_delete(self, ini_preset):
        default_entry = 'default'

        preset_manager, qtbot = ini_preset
        preset_manager.entry = default_entry

        copy_name = 'acopy'
        preset_manager.copy_entry('acopy', bypass_dialog=True)
        assert copy_name in preset_manager.list_managed_entries()
        assert default_entry in preset_manager.list_managed_entries()

        preset_manager.delete_entry(default_entry, bypass_dialog=True)
        assert copy_name in preset_manager.list_managed_entries()
        assert default_entry not in preset_manager.list_managed_entries()


    def test_create(self, ini_preset):
        default_entry = 'default'

        preset_manager, qtbot = ini_preset
        preset_manager.entry = default_entry

        new_entry = 'anewentry'

        preset_manager.create_entry(new_entry, bypass_dialog=True)

        assert new_entry in preset_manager.list_managed_entries()







