# -*- coding: utf-8 -*-
"""
Created the 27/10/2022

@author: Sebastien Weber
"""

from pymodaq.daq_utils import math_utils


def __getattr__(name):
    if hasattr(math_utils, name):
        return getattr(math_utils, name)
    else:
        raise AttributeError
