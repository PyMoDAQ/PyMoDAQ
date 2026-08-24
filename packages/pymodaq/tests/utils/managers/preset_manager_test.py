# -*- coding: utf-8 -*-
"""
Created the 07/11/2023

@author: Sebastien Weber
"""
import pytest
import qt_themes
from qtpy import QtWidgets
from pymodaq.utils.managers.experiment.experiment_manager import ExperimentManager
from pymodaq_gui.parameter import Parameter
from pymodaq_gui.parameter import utils as putils
from pymodaq_gui.parameter import ioxml
from pymodaq_utils.config import GlobalConfig

config = GlobalConfig()


@pytest.fixture
def init_qt(qtbot):
    qt_themes.set_theme(
        theme=config('gui', 'style', 'theme')[0],
        style=config('gui', 'style', 'style')[0],
    )
    return qtbot


@pytest.fixture
def ini_experiment(init_qt):

    qtbot = init_qt

    external_ui = QtWidgets.QMainWindow()

    experiment_manager = ExperimentManager()
    experiment_manager.update_entry()
    qtbot.addWidget(experiment_manager.mainwindow)
    experiment_manager.mainwindow.show()
    qtbot.addWidget(external_ui)

    yield experiment_manager, qtbot

    experiment_manager.quit_fun()
    external_ui.close()


class TestExperimentManager:

    def test_ini(self, ini_experiment):
        """
        """
        experiment_manager, qtbot = ini_experiment

        assert experiment_manager.entry_type == 'experiment'
        assert experiment_manager.entry_extension == '.xml'

    def test_default(self, ini_experiment):
        """
        """
        experiment_manager, qtbot = ini_experiment
        experiment_manager.entry = 'default'

        path = experiment_manager.get_entry_folder().joinpath('default.xml')
        param_dict = ioxml.xml_file_to_parameter_dict(path)
        pobject = Parameter.create(**param_dict)
        assert putils.compareParameters(pobject, experiment_manager.settings, with_self=False)

    def test_copy(self, ini_experiment):
        experiment_manager, qtbot = ini_experiment
        experiment_manager.entry = 'default'

        default_state = experiment_manager.settings.saveState()


        copy_name = 'acopy'

        experiment_manager.copy_entry('acopy', bypass_dialog=True)

        assert copy_name == experiment_manager.entry
        assert copy_name in experiment_manager.list_managed_entries()

        copy_state = experiment_manager.settings.saveState()

        assert default_state == copy_state

        assert copy_name in [
            experiment_manager.get_action_list().itemText(ind) for ind in
            range(experiment_manager.get_action_list().count())]

    def test_delete(self, ini_experiment):
        default_entry = 'default'

        experiment_manager, qtbot = ini_experiment
        experiment_manager.entry = default_entry

        copy_name = 'acopy'
        experiment_manager.copy_entry('acopy', bypass_dialog=True)
        assert copy_name in experiment_manager.list_managed_entries()
        assert default_entry in experiment_manager.list_managed_entries()

        experiment_manager.delete_entry(copy_name, bypass_dialog=True)
        assert copy_name not in experiment_manager.entries
        assert copy_name not in experiment_manager.list_managed_entries()  # should be the same as above
        assert default_entry in experiment_manager.list_managed_entries()

        experiment_manager.delete_entry(default_entry, bypass_dialog=True)
        assert default_entry in experiment_manager.entries  #the default entry is always recreated!


    def test_create(self, ini_experiment):
        default_entry = 'default'

        experiment_manager, qtbot = ini_experiment
        experiment_manager.entry = default_entry

        new_entry = 'anewentry'

        experiment_manager.create_entry(new_entry, bypass_dialog=True)

        assert new_entry in experiment_manager.list_managed_entries()







