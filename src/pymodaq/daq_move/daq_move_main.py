# -*- coding: utf-8 -*-
"""
Created the 25/09/2022

@author: Sebastien Weber
"""
from ..daq_utils.messenger import deprecation_msg
from ..control_modules.daq_move import DAQ_Move


deprecation_msg('Importing DAQ_Move from pymodaq.daq_move.daq_move_main module is deprecated \n'
                'import from pymodaq.control_modules.daq_move')