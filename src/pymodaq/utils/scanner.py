# -*- coding: utf-8 -*-
"""
Created the 27/10/2022

@author: Sebastien Weber
"""

from pymodaq.daq_utils import scanner


def __getattr__(name):
    if hasattr(scanner, name):
        return getattr(scanner, name)
    else:
        raise AttributeError