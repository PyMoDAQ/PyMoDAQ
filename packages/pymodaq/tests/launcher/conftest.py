import shutil
from pathlib import Path

import pytest

from pymodaq.utils.config import get_set_configurator_path, get_set_experiment_path


@pytest.fixture
def copied_data(tmp_path):
    """Setup fixture: copy test data files to appropriate system directories"""
    # Set up paths
    configurator_path = get_set_configurator_path()
    user_configuration_path = get_set_experiment_path(user=True)
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