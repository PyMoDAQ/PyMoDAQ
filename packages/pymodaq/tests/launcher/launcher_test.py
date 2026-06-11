import sys

import pytest
from qtpy import QtWidgets

from pymodaq_utils.config import GlobalConfig, get_set_local_dir

config = GlobalConfig()


class TestLauncher:

    def test_next_arrow_disabled(self, launcher):
        assert launcher.get_action('next_config').isEnabled() == False

    def test_back_arrow_disabled_next_arrow_enabled(self, launcher):
        launcher.do_navigate(len(launcher.history) - 1)
        assert launcher.get_action('next_config').isEnabled() == True
        assert launcher.get_action('back_config').isEnabled() == False

    def test_informations_from_history_file(self, launcher):

        # History size
        assert len(launcher.history) == 2

        # Test ten value
        assert launcher.date_combo_box.currentText() == '2026/04/20 at 10h16'
        assert launcher.experiment_manager.entry == 'exp_test'
        assert launcher.experiment_manager.get_action_list().currentText() == 'exp_test'
        assert launcher.state_manager.entry == 'ten_value'
        QtWidgets.QApplication.processEvents()
        assert launcher.state_manager.get_action_list().currentText() == 'ten_value'

        # Navigate in the back config
        launcher.do_navigate(launcher.history_index + 1)
        QtWidgets.QApplication.processEvents()

        # Test hundred value
        assert launcher.date_combo_box.currentText() == '2026/04/20 at 10h15'
        assert launcher.experiment_manager.entry == 'exp_test'
        assert launcher.experiment_manager.get_action_list().currentText() == 'exp_test'
        assert launcher.state_manager.entry == 'hundred_value'
        assert launcher.state_manager.get_action_list().currentText() == 'hundred_value'


    @pytest.mark.parametrize('launcher', ['history_test_duplicates.toml'], indirect=True)
    def test_history_duplicates_false(self, launcher):
        config['pymodaq', 'launcher', 'keep_duplicates'] = False
        launcher.state_manager.history_file_path = (
            str(get_set_local_dir(user=True).joinpath('history_test_duplicates.toml')))
        launcher.state_manager.save_new_history_entry()
        launcher._on_history_file_modified()
        assert len(launcher.history) == 2

    @pytest.mark.parametrize('launcher', ['history_test_duplicates.toml'], indirect=True)
    def test_history_duplicates_true(self, launcher):
        config['pymodaq', 'launcher', 'keep_duplicates'] = True
        launcher.state_manager.history_file_path = (
            str(get_set_local_dir(user=True).joinpath('history_test_duplicates.toml')))
        launcher.state_manager.save_new_history_entry()
        launcher._on_history_file_modified()
        assert len(launcher.history) == 6 # save_new_history_entry write a new entry in the history file


