
from pathlib import Path

try:
    from pymodaq_gui.config_saver_loader import get_set_roi_path
except ModuleNotFoundError:
    from pymodaq_gui.config import get_set_roi_path

from pymodaq_utils.config import (GlobalConfig, BaseConfig, ConfigError, get_set_config_dir,
                                  USER, CONFIG_BASE_PATH, get_set_local_dir)


def get_set_preset_path(user=False):
    """ creates and return the config folder path for managers files
    """
    return get_set_config_dir('preset_configs', user=user)


def get_set_configurator_path(subfolder: str = '', user=False):
    """ creates and return the config folder path for managers files
    """
    target_path = get_set_config_dir('configurator_configs', user=user).joinpath(subfolder)
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


def get_set_layout_path(user=False):
    """ creates and return the config folder path for layout files
    """
    return get_set_config_dir('layout_configs', user=user)


def get_set_remote_path(user=False):
    """ creates and return the config folder path for remote (shortcuts or joystick) files
    """
    return get_set_config_dir('remote_configs', user=user)


def get_set_overshoot_path(user=False):
    """ creates and return the config folder path for overshoot files
    """
    return get_set_config_dir('overshoot_configs', user=user)

@GlobalConfig.register()
class Config(BaseConfig):
    """Main class to deal with configuration values for this plugin"""
    config_template_path = Path(__file__).parent.parent.joinpath('resources/config_template.toml')
    config_name = f"pymodaq"

