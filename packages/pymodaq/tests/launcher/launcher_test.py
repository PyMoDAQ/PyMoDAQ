import pytest
from qtpy.QtCore import Qt
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
    """Fixture pour initialiser un Configurator avec son interface isolée"""
    qt_themes.set_theme(theme=config('gui', 'style', 'theme')[0],
                        style=config('gui', 'style', 'style')[0])

    try:
        # Importer ici pour éviter les dépendances circulaires
        from pymodaq.utils.managers.configurator.configurator import Configurator

        # Créer le configurator
        configurator = Configurator()

        # Créer la fenêtre principale
        main_window = QtWidgets.QMainWindow()
        main_window.setWindowTitle('Bug sync')

        # Ajouter le toolbar du configurator comme widget central
        main_window.setCentralWidget(configurator.add_toolbar('test'))

        # Configurer les menus externes
        configurator.experiment_manager.get_external_toolbar_menu(toolbar=configurator.get_toolbar('test'))
        configurator.get_external_toolbar_menu(toolbar=configurator.get_toolbar('test'))

        # Activer les actions
        configurator.experiment_manager.enable_actions(True)
        configurator.enable_actions(True)

        # Ajouter à qtbot
        qtbot.addWidget(main_window)
        main_window.show()

        yield configurator, main_window, qtbot

        # Nettoyage
        main_window.close()
        main_window.deleteLater()
    except Exception as e:
        pytest.skip(f"Configurator not available: {str(e)}")


class TestWidgetSync:
    def test_ini(self, ini_configurator):
        """Test initialization of Configurator interface"""
        configurator, main_window, qtbot = ini_configurator
        main_window.show()
        qtbot.wait(500)

    def test_experiment_entries(self, ini_configurator):
        configurator, main_window, qtbot = ini_configurator
        main_window.show()
        qtbot.wait(2000)
        experiments = configurator.experiment_manager.entries

        if len(experiments) > 1:
            index = 1
        else :
            index = 0
        configurator.experiment_manager.entry = experiments[index]
        qtbot.wait(2000)
        assert configurator.entry == 'default'
        configurator.quit_fun()

    def test_default_configuration(self, ini_configurator):
        configurator, main_window, qtbot = ini_configurator
        main_window.show()
        config_filepath_1 = configurator.entry_filepath
        configurator.experiment_manager.entry = configurator.experiment_manager.entries[-1]
        config_filepath_2 = configurator.entry_filepath

        assert config_filepath_1 != config_filepath_2

    def test_configuration_filepath(self, ini_configurator):
        configurator, main_window, qtbot = ini_configurator
        main_window.show()
        liste1 = configurator.entries_filepath
        configurator.experiment_manager.entry = configurator.experiment_manager.entries[-1]
        liste2 = configurator.entries_filepath

        assert liste1 != liste2
        for elt in liste1:
            if elt in liste2:
                assert False




