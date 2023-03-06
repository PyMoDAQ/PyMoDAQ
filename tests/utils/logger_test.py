# -*- coding: utf-8 -*-
"""
Created the 28/10/2022

@author: Sebastien Weber
"""
from pymodaq.utils import config as config_mod
from pymodaq.utils import logger as logger_mod


def test_get_module_name():
    config_path = config_mod.get_set_config_dir()
    assert logger_mod.get_module_name(config_path) == 'config'