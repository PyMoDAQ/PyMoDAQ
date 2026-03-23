# -*- coding: utf-8 -*-
"""
Created the 07/11/2023

@author: Sebastien Weber
"""
import pytest

from qtpy import QtWidgets
from pymodaq.utils.managers.preset.preset_manager import PresetManager
from pymodaq_gui.parameter import Parameter
from pymodaq_gui.parameter import utils as putils
from pymodaq_gui.parameter import ioxml

@pytest.fixture
def init_qt(qtbot):
    return qtbot


@pytest.fixture
def ini_preset(init_qt):

    qtbot = init_qt

    external_ui = QtWidgets.QMainWindow()

    preset_manager = PresetManager()
    preset_manager.update_entry()
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
        param_dict = ioxml.xml_file_to_parameter_dict(path)
        pobject = Parameter.create(**param_dict)
        assert putils.compareParameters(pobject, preset_manager.settings, with_self=False)

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
            preset_manager.get_action_list().itemText(ind) for ind in
            range(preset_manager.get_action_list().count())]

    def test_delete(self, ini_preset):
        default_entry = 'default'

        preset_manager, qtbot = ini_preset
        preset_manager.entry = default_entry

        copy_name = 'acopy'
        preset_manager.copy_entry('acopy', bypass_dialog=True)
        assert copy_name in preset_manager.list_managed_entries()
        assert default_entry in preset_manager.list_managed_entries()

        preset_manager.delete_entry(copy_name, bypass_dialog=True)
        assert copy_name not in preset_manager.entries
        assert copy_name not in preset_manager.list_managed_entries() # should be the same as above
        assert default_entry in preset_manager.list_managed_entries()

        preset_manager.delete_entry(default_entry, bypass_dialog=True)
        assert default_entry in preset_manager.entries  #the default entry is always recreated!


    def test_create(self, ini_preset):
        default_entry = 'default'

        preset_manager, qtbot = ini_preset
        preset_manager.entry = default_entry

        new_entry = 'anewentry'

        preset_manager.create_entry(new_entry, bypass_dialog=True)

        assert new_entry in preset_manager.list_managed_entries()







