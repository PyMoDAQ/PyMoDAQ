# -*- coding: utf-8 -*-
"""
Created the 24/10/2022

@author: Sebastien Weber
"""
from ..daq_utils.messenger import deprecation_msg
from pymodaq.control_modules.move_utility_classes import comon_parameters, comon_parameters_fun, main, DAQ_Move_base

deprecation_msg('Importing move utilities from pymodaq.daq_move.utility_classes is deprecated \n'
                'import from pymodaq.control_modules.move_utility_classes')
