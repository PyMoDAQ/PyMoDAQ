# -*- coding: utf-8 -*-
"""
Created the 26/10/2023

@author: Sebastien Weber
"""
from pymodaq_data.serialize.mysocket import Socket

from pymodaq_utils.utils import deprecation_msg

deprecation_msg('Importing Socket from pymodaq is deprecated in PyMoDAQ >= 5,'
                'import it from pymodaq_data.serialize.mysocket')