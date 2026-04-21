from qtpy import QtWidgets
from pymodaq_utils.config import GlobalConfig

config = GlobalConfig()




class TestLauncher:
    def test_ini(self, ini_launcher):
        launcher, qtbot = ini_launcher
        assert launcher is not None
        qtbot.wait(5000)

    def test_label(self, ini_launcher):
        launcher, qtbot = ini_launcher
        assert launcher.dashboard_button.text() == 'Dashboard'

    def test_restore(self, ini_launcher):
        launcher, qtbot = ini_launcher
        launcher.get_action('load_default_dashboard').trigger()
        qtbot.wait(500)

    def test_next_arrow(self, ini_launcher):
        launcher, qtbot = ini_launcher
        assert launcher.get_action('next_config').isEnabled() == False

    def test_back_arrow(self, ini_launcher):
        launcher, qtbot = ini_launcher
        launcher.do_navigate(len(launcher.history) - 1)
        assert launcher.get_action('next_config').isEnabled() == True
        assert launcher.get_action('back_config').isEnabled() == False

    def test_informations_from_history_file(self, ini_launcher, copied_data):
        launcher, qtbot = ini_launcher

        # History size
        assert len(launcher.history) == 2

        # Test ten value
        assert launcher.date_combo_box.currentText() == '2026/04/20 at 10h16'
        assert launcher.experiment_manager.entry == 'exp_test'
        assert launcher.experiment_manager.get_action_list().currentText() == 'exp_test'
        assert launcher.configurator.entry == 'ten_value'
        assert launcher.configurator.get_action_list().currentText() == 'ten_value'

        # Navigate in the back config
        launcher.do_navigate(launcher.history_index + 1)

        # Test hundred value
        assert launcher.date_combo_box.currentText() == '2026/04/20 at 10h15'
        assert launcher.experiment_manager.entry == 'exp_test'
        assert launcher.experiment_manager.get_action_list().currentText() == 'exp_test'
        assert launcher.configurator.entry == 'hundred_value'
        assert launcher.configurator.get_action_list().currentText() == 'hundred_value'




class TestWidgetSync:
    """Test displayed values."""

    def test_ini(self, ini_configurator, copied_data):
        """Test initialization of Configurator interface"""
        configurator, main_window, qtbot = ini_configurator
        main_window.show()
        qtbot.wait(5000)


    def test_widgets_synchro(self, ini_configurator, copied_data):
        configurator, main_window, qtbot = ini_configurator
        main_window.show()
        qtbot.wait(1000)

        assert configurator.experiment_manager.entry == 'default'
        assert configurator.experiment_manager.get_action_list().currentText() == 'default'

        configurator.experiment_manager.entry = 'exp_test'
        QtWidgets.QApplication.processEvents()
        qtbot.wait(500)

        assert configurator.experiment_manager.entry == 'exp_test'
        assert configurator.experiment_manager.get_action_list().currentText() == 'exp_test'
        assert 'ten_value' in configurator.entries
        assert 'hundred_value' in configurator.entries

        configurator.entry = 'hundred_value'
        qtbot.wait(500)

        assert configurator.entry == 'hundred_value'
        assert configurator.get_action_list().currentText() == 'hundred_value'
