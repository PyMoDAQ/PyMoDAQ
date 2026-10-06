
from pathlib import Path

from pymodaq_gui.config import get_set_roi_path, get_set_layout_path  # noqa

from pymodaq_utils.config import (GlobalConfig, BaseConfig, ConfigError, get_set_config_dir,
                                  USER, CONFIG_BASE_PATH, get_set_local_dir)


def get_set_experiment_path(user=False):
    """ creates and return the config folder path for managers files
    """
    return get_set_config_dir('experiments', user=user)


def get_set_state_path(subfolder: str = '', user=False):
    """ creates and return the config folder path for managers files
    """
    target_path = get_set_config_dir('states', user=user).joinpath(subfolder)
    target_path.mkdir(parents=True, exist_ok=True)
    
    return target_path

def get_set_batch_path(user=False):
    """ creates and return the config folder path for managers files
    """
    return get_set_config_dir('batch_configs', user=user)


def get_set_pid_path(user=False):
    """ creates and return the config folder path for PID files
    """
    return get_set_config_dir('pid_configs', user=user)


def get_set_remote_path(user=False):
    """ creates and return the config folder path for remote (shortcuts or joystick) files
    """
    return get_set_config_dir('remote_configs', user=user)


def get_set_overshoot_path(subfolder: str = '', user=False):
    """ creates and return the config folder path for the Overshoot Manager entries

    Entries are stored in a subfolder named from the experiment. Files from older versions may still be in the
    'overshoot_configs' folder, they are not used anymore.
    """
    target_path = get_set_config_dir('overshooter_configs', user=user).joinpath(subfolder)
    target_path.mkdir(parents=True, exist_ok=True)
    return target_path


def get_set_roi_manager_path(user=True):
    """ creates and return the config folder path for the ROI Manager entries (one file per experiment)

    Not to be confused with pymodaq_gui.config.get_set_roi_path, used by the data viewers to save their ROIs
    """
    return get_set_config_dir('rois', user=user)


@GlobalConfig.register()
class Config(BaseConfig):
    """Main class to deal with configuration values for this plugin"""
    config_template_path = Path(__file__).parent.parent.joinpath('resources/config_template.toml')
    config_name = f"pymodaq"

