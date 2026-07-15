import sys
from typing import Union

from qtpy.QtWidgets import QVBoxLayout, QToolBar
from qtpy import QtWidgets

import qt_themes

from pymodaq.control_modules.daq_move_ui.ui_base import DAQ_Move_UI_Base
from pymodaq.control_modules.thread_commands import UiToMainMove
from pymodaq_gui.qt_utils import mkQApp
from pymodaq_gui.utils.widgets import LabelWithFont

from pymodaq.utils.data import DataActuator

from pymodaq_utils.utils import ThreadCommand
from pymodaq_utils.config import Config

from pymodaq.control_modules.daq_move_ui.factory import ActuatorUIFactory
from pymodaq.control_modules.daq_move_ui.uis.simple import DAQ_Move_UI_Simple
from pymodaq_utils.config import GlobalConfig as Config
from enum import Enum

config = Config()


@ActuatorUIFactory.register('Binary')
class DAQ_Move_UI_Binary(DAQ_Move_UI_Simple):
    """ UI for Actuators where only two values are encoded: 0 or 1 for instance

    Some other numerical values can be set in the config: 'actuator', 'default_value_green'
    The green arrow button will fire the 'default_value_green' (can be updated/customized using the settings)
    The red arrow button will fire the 'default_value_red' (can be updated/customized using the settings)

    Could be used for 2 positions only actuators such as a Flip
    """


    is_compact = True

    def _setup_move_actions(self, toolbar: QtWidgets.QToolBar):
        self._setup_absolute_actions(toolbar)

    def setup_docks_and_widgets(self):
        super().setup_docks_and_widgets()
        self.abs_value_sb_red.setVisible(False)
        self.abs_value_sb_green.setVisible(False)
