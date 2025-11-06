# -*- coding: utf-8 -*-
"""
Created the 28/10/2022

@author: Sebastien Weber
"""
import pymodaq_utils
from pymodaq_utils import config as config_mod
from pymodaq_utils import logger as logger_mod


def test_get_module_name():
    config_path = config_mod.get_set_config_dir()
    assert logger_mod.get_module_name(config_path) == 'config'


def test_get_base_logger():
    logger = logger_mod.set_logger('random_name')
    assert logger_mod.get_base_logger(logger).name == 'pymodaq'
