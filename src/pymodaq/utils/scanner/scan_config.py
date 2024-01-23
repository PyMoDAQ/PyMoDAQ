# -*- coding: utf-8 -*-
"""
Created the 19/11/2023

@author: Sebastien Weber
"""

from pathlib import Path
from pymodaq.utils.config import BaseConfig, getitem_recursive


class ScanConfig(BaseConfig):
    """Main class to deal with configuration values for this plugin"""
    config_template_path = Path(__file__).parent.parent.parent.joinpath('resources/config_scan_template.toml')
    config_name = f"scanner_settings"

    def __setitem__(self, key, value):
        if isinstance(key, tuple):
            dic = getitem_recursive(self._config, *key, ndepth=1, create_if_missing=True)
            if value is None:  # means the setting is a group
                value = {}
            dic[key[-1]] = value
        else:
            self._config[key] = value