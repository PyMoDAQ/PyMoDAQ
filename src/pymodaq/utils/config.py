
from pathlib import Path

try:
    from pymodaq_gui.config_saver_loader import get_set_roi_path
except ModuleNotFoundError:
    from pymodaq_gui.config import get_set_roi_path

from pymodaq_utils.config import (BaseConfig, ConfigError, get_set_config_dir,
                                  USER, CONFIG_BASE_PATH, get_set_local_dir)


def get_set_preset_path():
    """ creates and return the config folder path for managers files
    """
    return get_set_config_dir('preset_configs')


def get_set_batch_path():
    """ creates and return the config folder path for managers files
    """
    return get_set_config_dir('batch_configs')


def get_set_pid_path():
    """ creates and return the config folder path for PID files
    """
    return get_set_config_dir('pid_configs')


def get_set_layout_path():
    """ creates and return the config folder path for layout files
    """
    return get_set_config_dir('layout_configs')


def get_set_remote_path():
    """ creates and return the config folder path for remote (shortcuts or joystick) files
    """
    return get_set_config_dir('remote_configs')


def get_set_overshoot_path():
    """ creates and return the config folder path for overshoot files
    """
    return get_set_config_dir('overshoot_configs')


class Config(BaseConfig):
    """Main class to deal with configuration values for this plugin"""
    config_template_path = Path(__file__).parent.parent.joinpath('resources/config_template.toml')
    config_name = f"config_pymodaq"

