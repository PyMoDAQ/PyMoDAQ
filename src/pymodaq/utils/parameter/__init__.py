# -*- coding: utf-8 -*-
"""
Created the 27/10/2022

@author: Sebastien Weber
"""

from pymodaq.daq_utils import parameter


def __getattr__(name):
    if hasattr(parameter, name):
        return getattr(parameter, name)
    else:
        raise AttributeError
