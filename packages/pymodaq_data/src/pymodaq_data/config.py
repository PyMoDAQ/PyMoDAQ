from pathlib import Path

from pymodaq_utils.config import (GlobalConfig, BaseConfig)


@GlobalConfig.register()
class Config(BaseConfig):
    """Main class to deal with configuration values for this plugin"""
    config_template_path = Path(__file__).parent.joinpath('resources/config_template.toml')
    config_name = f"data"

