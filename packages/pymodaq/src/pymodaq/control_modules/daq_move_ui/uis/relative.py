import sys

from qtpy.QtWidgets import QVBoxLayout, QToolBar
from qtpy import QtWidgets
import qt_themes

from pymodaq.control_modules.daq_move_ui.ui_base import DAQ_Move_UI_Base
from pymodaq.control_modules.thread_commands import UiToMainMove
from pymodaq_gui.qt_utils import mkQApp
from pymodaq_gui.utils.widgets import LabelWithFont
from pymodaq_utils.utils import ThreadCommand

from pymodaq.control_modules.daq_move_ui.factory import ActuatorUIFactory


@ActuatorUIFactory.register('Relative')
class DAQ_Move_UI_Relative(DAQ_Move_UI_Base):
    is_compact = True
    def __init__(self, parent, title="DAQ_Move", **kwargs):

        super().__init__(parent, title, **kwargs)

    def setup_docks_and_widgets(self):
        super().setup_docks_and_widgets()

        self.parent.setLayout(QtWidgets.QHBoxLayout())
        self.parent.layout().setContentsMargins(0, 0, 0, 0)

        self.current_value_sb.set_font_size(10)
        self.current_value_sb.setMinimumHeight(20)
        self.current_value_sb.setMinimumWidth(80)

    def setup_actions(self):
        self.setup_actions_in_toolbar(self.toolbar)
        self.set_action_visible('show_controls', False)
        self.set_action_visible('show_graph', False)
        self.set_action_visible('refresh_value', False)

    def _setup_move_actions(self, toolbar: QtWidgets.QToolBar):
        self._setup_relative_actions(self.toolbar)


    def connect_things(self):
        super().connect_things()

        self.connect_action('move_rel_plus', lambda: self.emit_move_rel('+'))
        self.connect_action('move_rel_minus', lambda: self.emit_move_rel('-'))

