import sys

from PyQt6.QtWidgets import QVBoxLayout, QToolBar
from qtpy import QtWidgets

from pymodaq.control_modules.daq_move_ui.ui_base import DAQ_Move_UI_Base
from pymodaq.control_modules.thread_commands import UiToMainMove
from pymodaq_gui.utils.widgets import LabelWithFont
from pymodaq_utils.utils import ThreadCommand

from pymodaq.control_modules.daq_move_ui.factory import ActuatorUIFactory


@ActuatorUIFactory.register('Binary')
class DAQ_Move_UI_Binary(DAQ_Move_UI_Base):
    def __init__(self, parent, title="DAQ_Move"):

        super().__init__(parent, title)


