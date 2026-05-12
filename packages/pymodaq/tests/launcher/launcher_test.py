import pytest
from qtpy import QtWidgets

from pymodaq.utils.managers.state.state_manager import StateManager
from pymodaq_utils.config import GlobalConfig
from mock import patch
from subprocess import Popen

config = GlobalConfig()


class TestLauncher:

    def test_next_arrow_disabled(self, launcher):
        assert launcher.get_action('next_config').isEnabled() == False

    def test_back_arrow_disabled_next_arrow_enabled(self, launcher):
        launcher.do_navigate(len(launcher.history) - 1)
        assert launcher.get_action('next_config').isEnabled() == True
        assert launcher.get_action('back_config').isEnabled() == False

    def test_informations_from_history_file(self, launcher, qtbot):

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

    @patch('subprocess.Popen')
    def test_restore(self, mock_popen, qtbot, launcher):
        """
        Mock 'subprocess.Popen' method to test if the launcher passes the correct arguments to the dashboard command.

        Limits of this test:
        To restore a dashboard, the launcher passes experiment and state names to the dashboard command.
        But the launcher and the dashboard run in separate processes, the dashboard is a subprocess of the launcher.
        So direct communication between them is impossible. This test verifies that the launcher passes the correct
        arguments, but the responsibility of the correct launch belongs to the dashboard via the 'load_dashboard_with_preset' method.
        """
        launcher.get_action('restore_dashboard').trigger()
        qtbot.waitUntil(lambda: mock_popen.called, timeout=5000)
        assert mock_popen.called

        # Get arguments list
        args_list = mock_popen.call_args[0][0]

        # Verify command arguments
        assert args_list[0] == 'dashboard'
        assert args_list[1] == '-x'
        assert args_list[2] == 'exp_test'
        assert args_list[3] == '-c'
        assert args_list[4] == 'ten_value'


    @pytest.mark.parametrize('launcher', ['history_test_duplicates.toml'], indirect=True)
    def test_history_duplicates_false(self, launcher):
        config['pymodaq', 'launcher', 'keep_duplicates'] = False
        launcher.state_manager.history_file_name = 'history_test_duplicates.toml'
        launcher.state_manager.save_new_history_entry()
        launcher._on_history_file_modified()
        assert len(launcher.history) == 2

    @pytest.mark.parametrize('launcher', ['history_test_duplicates.toml'], indirect=True)
    def test_history_duplicates_true(self, launcher):
        config['pymodaq', 'launcher', 'keep_duplicates'] = True
        launcher.state_manager.history_file_name = 'history_test_duplicates.toml'
        launcher.state_manager.save_new_history_entry()
        launcher._on_history_file_modified()
        assert len(launcher.history) == 6 # save_new_history_entry write a new entry in the history file


class TestWidgetSync:
    """Test displayed values."""

    def test_widgets_synchro(self, qtbot, main_window, state_manager, copied_data):
        main_window.show()
        qtbot.waitExposed(main_window, timeout=5000)

        assert state_manager.experiment_manager.entry == 'default'
        assert state_manager.experiment_manager.get_action_list().currentText() == 'default'

        with qtbot.waitSignal(state_manager.experiment_manager.entries_sync.value_changed, timeout=5000):
            state_manager.experiment_manager.entry = 'exp_test'

        QtWidgets.QApplication.processEvents()

        assert state_manager.experiment_manager.entry == 'exp_test'
        assert state_manager.experiment_manager.get_action_list().currentText() == 'exp_test'
        assert 'ten_value' in state_manager.entries
        assert 'hundred_value' in state_manager.entries

        state_manager.entry = 'hundred_value'
        qtbot.waitExposed(main_window, timeout=5000)

        assert state_manager.entry == 'hundred_value'
        assert state_manager.get_action_list().currentText() == 'hundred_value'
