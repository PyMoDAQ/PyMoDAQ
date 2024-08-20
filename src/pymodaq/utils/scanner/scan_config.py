# -*- coding: utf-8 -*-
"""
Created the 19/11/2023

@author: Sebastien Weber
"""

from pathlib import Path
from pymodaq_utils.config import BaseConfig


class ScanConfig(BaseConfig):
    """Main class to deal with configuration values for this plugin"""
    config_template_path = None
    config_name = f"scanner_settings"

