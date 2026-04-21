import shutil
from pathlib import Path

import pytest
from qtpy import QtWidgets

from pymodaq.launcher.launcher import Launcher
import qt_themes

from pymodaq_utils.config import GlobalConfig

from pymodaq.utils.config import get_set_configurator_path, get_set_experiment_path

config = GlobalConfig()

@pytest.fixture
def copied_data(tmp_path):
    """Setup fixture: copy test data files to appropriate system directories"""
    # Set up paths
    configurator_path = get_set_configurator_path()
    user_configuration_path = get_set_configurator_path(user=True)
    experiment_path = get_set_experiment_path()
    test_directory = Path(__file__).parent
    ressources_directory = test_directory / 'ressources'

    # Copy test files to pymodaq directories
    shutil.copy(str(ressources_directory / 'exp_test.xml'), str(experiment_path / 'exp_test.xml'))
    shutil.copy(str(ressources_directory / 'history_test.toml'), str(user_configuration_path / 'history_test.toml'))
    shutil.copytree(ressources_directory / 'exp_test', configurator_path / 'exp_test', dirs_exist_ok=True)

    yield

    # Cleanup: remove all copied files after test execution
    (experiment_path / 'exp_test.xml').unlink(missing_ok=True)
    (user_configuration_path / 'history_test.toml').unlink(missing_ok=True)
    shutil.rmtree(configurator_path / 'exp_test', ignore_errors=True)

@pytest.fixture
def ini_launcher(qtbot, copied_data):
    """Fixture to initialize launcher with Qt widget"""
    qt_themes.set_theme(theme=config('gui', 'style', 'theme')[0],
                        style=config('gui', 'style', 'style')[0])
    external_ui = QtWidgets.QMainWindow()
    launcher = Launcher(external_ui, history_file_name='history_test.toml') # Use the test history file to isolate data tests and data production

    qtbot.addWidget(external_ui)
    launcher.mainwindow.show()

    yield launcher, qtbot

    # Clean up
    launcher.quit_fun()
    launcher.mainwindow.close()
    external_ui.close()

