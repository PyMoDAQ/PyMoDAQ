# -*- coding: utf-8 -*-
"""
Created the 27/10/2022

@author: Sebastien Weber
"""

from pymodaq.daq_utils import daq_utils


def __getattr__(name):
    if hasattr(daq_utils, name):
        return getattr(daq_utils, name)
    else:
        raise AttributeError
