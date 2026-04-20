import pytest

from qtpy import QtWidgets

from pymodaq.launcher.launcher import Launcher
import qt_themes

from pymodaq_utils.config import GlobalConfig

config = GlobalConfig()


@pytest.fixture
def ini_launcher(qtbot):
    """Fixture pour initialiser un Launcher avec le widget Qt"""
    qt_themes.set_theme(theme=config('gui', 'style', 'theme')[0],
                        style=config('gui', 'style', 'style')[0])
    external_ui = QtWidgets.QMainWindow()
    launcher = Launcher(external_ui)

    qtbot.addWidget(external_ui)  # Ajouter le QMainWindow à qtbot, pas le Launcher
    launcher.mainwindow.show()

    yield launcher, qtbot

    # Nettoyage après le test
    launcher.quit_fun()
    launcher.mainwindow.close()
    external_ui.close()


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


@pytest.fixture
def ini_configurator(qtbot):
    """Fixture to replicate the synchronization bug between experiment and configuration."""
    qt_themes.set_theme(theme=config('gui', 'style', 'theme')[0],
                        style=config('gui', 'style', 'style')[0])

    try:
        from pymodaq.utils.managers.configurator.configurator import Configurator

        configurator = Configurator()

        main_window = QtWidgets.QMainWindow()
        main_window.setWindowTitle('Bug sync')
        main_window.setCentralWidget(configurator.add_toolbar('test'))

        configurator.experiment_manager.get_external_toolbar_menu(toolbar=configurator.get_toolbar('test'))
        configurator.get_external_toolbar_menu(toolbar=configurator.get_toolbar('test'))
        configurator.experiment_manager.enable_actions(True)
        configurator.enable_actions(True)

        qtbot.addWidget(main_window)
        main_window.show()

        yield configurator, main_window, qtbot

        main_window.close()
        main_window.deleteLater()
    except Exception as e:
        pytest.skip(f"Configurator not available: {str(e)}")


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


