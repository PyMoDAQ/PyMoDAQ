# -*- coding: utf-8 -*-
"""
Created the 25/09/2022

@author: Sebastien Weber
"""
from ..daq_utils.messenger import deprecation_msg
from ..control_modules.daq_viewer import DAQ_Viewer

deprecation_msg('Importing DAQ_Viewer from pymodaq.daq_viewer.daq_viewer_main module is deprecated \n'
                'import from pymodaq.control_modules.daq_viewer')