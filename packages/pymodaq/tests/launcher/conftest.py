import shutil
from pathlib import Path

import pytest
from qtpy import QtWidgets

from pymodaq.launcher.launcher import Launcher
import qt_themes

from pymodaq_utils.config import GlobalConfig, get_set_local_dir

from pymodaq.utils.config import get_set_state_path, get_set_experiment_path

config = GlobalConfig()

@pytest.fixture
def copied_data(tmp_path):
    """Setup fixture: copy test data files to appropriate system directories"""
    # Set up paths
    keep_duplicates = config['pymodaq', 'launcher', 'keep_duplicates']
    state_path = get_set_state_path()
    user_path = get_set_local_dir(user=True)
    experiment_path = get_set_experiment_path()
    test_directory = Path(__file__).parent
    resources_directory = test_directory.joinpath('resources')

    # Copy test files to pymodaq directories
    shutil.copy(str(resources_directory.joinpath('exp_test.xml')),
                str(experiment_path.joinpath('exp_test.xml')))
    shutil.copy(str(resources_directory.joinpath('history_test.toml')),
                str(user_path.joinpath('history_test.toml')))
    shutil.copy(str(resources_directory.joinpath('history_test_duplicates.toml')),
                str(user_path.joinpath('history_test_duplicates.toml')))
    shutil.copytree(str(resources_directory.joinpath('exp_test')),
                    str(state_path.joinpath('exp_test')), dirs_exist_ok=True)

    yield

    # Cleanup: remove all copied files after test execution
    experiment_path.joinpath('exp_test.xml').unlink(missing_ok=True)
    user_path.joinpath('history_test.toml').unlink(missing_ok=True)
    user_path.joinpath('history_test_duplicates.toml').unlink(missing_ok=True)
    shutil.rmtree(state_path.joinpath('exp_test'), ignore_errors=True)
    config['pymodaq', 'launcher', 'keep_duplicates'] = keep_duplicates # restore initial application settings after tests execution

@pytest.fixture
def launcher(qtbot, copied_data, request):
    """Fixture to initialize launcher with Qt widget"""
    qt_themes.set_theme(theme=config('gui', 'style', 'theme')[0],
                        style=config('gui', 'style', 'style')[0])
    mainwindow = QtWidgets.QMainWindow()

    history_file = getattr(request, 'param', 'history_test.toml')
    launcher = Launcher(mainwindow, history_file_name=history_file)
    qtbot.addWidget(mainwindow)
    launcher.mainwindow.show()

    yield launcher

    # Clean up
    launcher.quit_fun()
    launcher.deleteLater()


@pytest.fixture
def state_manager(qtbot):
    """Fixture to replicate the synchronization bug between experiment and configuration."""
    qt_themes.set_theme(theme=config('gui', 'style', 'theme')[0],
                        style=config('gui', 'style', 'style')[0])

    try:
        from pymodaq.utils.managers.state.state_manager import StateManager

        state_manager = StateManager()

        main_window = QtWidgets.QMainWindow()
        main_window.setWindowTitle('Bug sync')
        main_window.setCentralWidget(state_manager.add_toolbar('test'))

        state_manager.experiment_manager.get_external_toolbar_menu(toolbar=state_manager.get_toolbar('test'))
        state_manager.get_external_toolbar_menu(toolbar=state_manager.get_toolbar('test'))
        state_manager.experiment_manager.enable_actions(True)
        state_manager.enable_actions(True)

        qtbot.addWidget(main_window)
        main_window.show()

        yield state_manager

        main_window.close()
        main_window.deleteLater()
    except Exception as e:
        pytest.skip(f"Configurator not available: {str(e)}")
