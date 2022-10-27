# -*- coding: utf-8 -*-
"""
Created the 27/10/2022

@author: Sebastien Weber
"""

from pymodaq.daq_utils import array_manipulation


def __getattr__(name):
    if hasattr(array_manipulation, name):
        return getattr(array_manipulation, name)
    else:
        raise AttributeError
