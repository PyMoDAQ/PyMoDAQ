from pathlib import Path

from pymodaq_utils.config import (GlobalConfig, BaseConfig, get_set_config_dir)


class Config(BaseConfig):
    """Main class to deal with configuration values for this plugin"""
    config_template_path = Path(__file__).parent.joinpath('resources/config_template.toml')
    config_name = f"gui"


def get_set_layout_path(user=False):
    """ creates and return the config folder path for layout files
    """
    return get_set_config_dir('layout_configs', user=user)


def get_set_roi_path():
    """ creates and return the config folder path for managers files
    """
    return get_set_config_dir('roi_configs')
