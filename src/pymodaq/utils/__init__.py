# -*- coding: utf-8 -*-
"""
Created the 27/10/2022

@author: Sebastien Weber
"""
import sys

from pymodaq.daq_utils.messenger import deprecation_msg, messagebox
from pymodaq.daq_utils.daq_utils import get_version
from qtpy.QtWidgets import QApplication


def __getattr__(name):
    msg = f'\n\n'\
          f'************************************************************************\n'\
          f'************************************************************************\n'\
          f'Your version ({get_version()}) of pymodaq is deprecated  compared to your\n'\
          f'plugins, please move to the latest version (v4.x.y and older) which is\n'\
          f'compatible with new and older plugins\n'\
          f'The issue is related to the calling of *pymodaq.utils.xxxx* modules meant to ' \
          f'be created into the v4+ version of pymodaq. If you want to make your plugins work with' \
          f'both please use pymodaq.daq_utils.xxxx instead '\
          f'************************************************************************\n'\
          f'************************************************************************\n'
    app = QApplication(sys.argv)
    messagebox(severity='warning', title='Incompatible Version', text=msg)
    sys.exit(app.exec_())
    raise AttributeError
