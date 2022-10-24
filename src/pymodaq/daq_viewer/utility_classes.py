# -*- coding: utf-8 -*-
"""
Created the 11/10/2022

@author: Sebastien Weber
"""
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, main, comon_parameters
from ..daq_utils.messenger import deprecation_msg

deprecation_msg('Importing DAQ_Viewer_base from pymodaq.daq_viewer.utility_classes module is deprecated \n'
                'import from pymodaq.control_modules.viewer_utility_classes', 3)
