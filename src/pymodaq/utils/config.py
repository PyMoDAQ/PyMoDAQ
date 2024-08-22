from pymodaq_utils.config import (BaseConfig, Config, ConfigError, get_set_config_dir,
                                  USER, CONFIG_BASE_PATH, get_set_local_dir)
from pymodaq_gui.config import get_set_roi_path


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





