# -*- coding: utf-8 -*-
"""
Created the 19/11/2023

@author: Sebastien Weber
"""
from typing import List
from abc import abstractproperty
from pathlib import Path
from pymodaq.utils.config import BaseConfig, getitem_recursive, ConfigError
from pymodaq.utils.parameter import utils as putils
from pymodaq.utils.parameter import Parameter


class BayesianConfig(BaseConfig):
    """Main class to deal with configuration values for this plugin"""
    config_template_path = None
    config_name = f"bayesian_settings"

