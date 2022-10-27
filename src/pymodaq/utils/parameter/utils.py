# -*- coding: utf-8 -*-
"""
Created the 27/10/2022

@author: Sebastien Weber
"""

from pymodaq.daq_utils.parameter import utils


def __getattr__(name):
    if hasattr(utils, name):
        return getattr(utils, name)
    else:
        raise AttributeError
