from qtpy.QtCore import Qt
from qtpy.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QToolBar, QGridLayout
from qtpy import QtWidgets

from pymodaq.control_modules.daq_move_ui.uis.simple import DAQ_Move_UI_Simple
from pymodaq.control_modules.thread_commands import UiToMainMove
from pymodaq_data import DataToExport
from pymodaq_gui.plotting.data_viewers import ViewerDispatcher
from pymodaq_gui.utils import DockArea
from pymodaq_gui.utils.widgets import LabelWithFont
from pymodaq_utils.utils import ThreadCommand


from ..factory import ActuatorUIFactory


@ActuatorUIFactory.register('Original')
class DAQ_Move_UI(DAQ_Move_UI_Simple):
    pass

# this UIs is not meant to be used anymore, it is kept here for backcompatibility but just
# now looks like the Simple UI
# Only when using standalone DAQ_Move, you'll have a UI looking kind of as before