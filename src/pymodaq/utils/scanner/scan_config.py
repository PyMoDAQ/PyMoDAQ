# -*- coding: utf-8 -*-
"""
Created the 19/11/2023

@author: Sebastien Weber
"""

from pathlib import Path
from pymodaq.utils.config import BaseConfig, getitem_recursive


class ScanConfig(BaseConfig):
    """Main class to deal with configuration values for this plugin"""
    config_template_path = None
    config_name = f"scanner_settings"

