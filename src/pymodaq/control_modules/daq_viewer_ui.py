# -*- coding: utf-8 -*-
"""
Created the 05/09/2022

@author: Sebastien Weber
"""


from typing import List
import sys

from qtpy import QtWidgets
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QHBoxLayout, QVBoxLayout, QGridLayout, QWidget, QToolBar, QComboBox

from pymodaq.daq_utils.daq_utils import ThreadCommand
from pymodaq.daq_utils.gui_utils.custom_app import CustomApp
from pymodaq.daq_utils.gui_utils.widgets import PushButtonIcon, LabelWithFont, SpinBox, QSpinBox_ro, QLED


class DAQ_Viewer_UI(CustomApp):
    """DAQ_Viewer user interface.

    This class manages the UI and emit dedicated signals depending on actions from the user

    Attributes
    ----------
    command_sig: Signal[Threadcommand]
        This signal is emitted whenever some actions done by the user has to be
        applied on the main module. Possible commands are:
            * init
            * quit
            * get_value
            * loop_get_value
            * find_home
            * stop
            * move_abs
            * move_rel
            * show_log
            * actuator_changed
            * rel_value

    Methods
    -------
    display_value(value: float)
        Update the display of the actuator's value on the UI
    do_init()
        Programmatic init

    See Also
    --------
    pymodaq.daq_utils.daq_utils.ThreadCommand
    """

    command_sig = Signal(ThreadCommand)

    def __init__(self, dockarea, title="DAQ_Viewer"):
        super().__init__(dockarea)
        self.title = title
        self.setup_ui()
