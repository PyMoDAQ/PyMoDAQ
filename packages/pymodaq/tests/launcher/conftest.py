import shutil
from pathlib import Path

import pytest
from qtpy import QtWidgets

from pymodaq.launcher.launcher import Launcher
import qt_themes

from pymodaq_utils.config import GlobalConfig, get_set_local_dir

from pymodaq.utils.config import get_set_configurator_path, get_set_experiment_path

config = GlobalConfig()

@pytest.fixture
def copied_data(tmp_path):
    """Setup fixture: copy test data files to appropriate system directories"""
    # Set up paths
    keep_duplicates = config['pymodaq', 'launcher', 'keep_duplicates']
    configurator_path = get_set_configurator_path()
    user_path = get_set_local_dir(user=True)
    experiment_path = get_set_experiment_path()
    test_directory = Path(__file__).parent
    ressources_directory = test_directory / 'ressources'

    # Copy test files to pymodaq directories
    shutil.copy(str(ressources_directory / 'exp_test.xml'), str(experiment_path / 'exp_test.xml'))
    shutil.copy(str(ressources_directory / 'history_test.toml'), str(user_path / 'history_test.toml'))
    shutil.copy(str(ressources_directory / 'history_test_duplicates.toml'), str(user_path / 'history_test_duplicates.toml'))
    shutil.copytree(ressources_directory / 'exp_test', configurator_path / 'exp_test', dirs_exist_ok=True)

    yield

    # Cleanup: remove all copied files after test execution
    (experiment_path / 'exp_test.xml').unlink(missing_ok=True)
    (user_path / 'history_test.toml').unlink(missing_ok=True)
    (user_path / 'history_test_duplicates.toml').unlink(missing_ok=True)
    shutil.rmtree(configurator_path / 'exp_test', ignore_errors=True)
    config['pymodaq', 'launcher', 'keep_duplicates'] = keep_duplicates # restore initial application settings after tests execution

@pytest.fixture
def launcher(qtbot, copied_data, request):
    """Fixture to initialize launcher with Qt widget"""
    qt_themes.set_theme(theme=config('gui', 'style', 'theme')[0],
                        style=config('gui', 'style', 'style')[0])
    external_ui = QtWidgets.QMainWindow()

    history_file = getattr(request, 'param', 'history_test.toml')
    launcher = Launcher(external_ui, history_file_name=history_file)
    qtbot.addWidget(external_ui)
    launcher.mainwindow.show()

    yield launcher

    # Clean up
    launcher.quit_fun()
    launcher.mainwindow.close()
    launcher.deleteLater()
    external_ui.close()


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

        yield configurator, main_window

        main_window.close()
        main_window.deleteLater()
    except Exception as e:
        pytest.skip(f"Configurator not available: {str(e)}")
