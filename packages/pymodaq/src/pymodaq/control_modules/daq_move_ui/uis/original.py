from qtpy.QtCore import Qt
from qtpy.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QToolBar, QGridLayout
from qtpy import QtWidgets

from pymodaq.control_modules.daq_move_ui.ui_base import DAQ_Move_UI_Base
from pymodaq.control_modules.thread_commands import UiToMainMove
from pymodaq_data import DataToExport
from pymodaq_gui.plotting.data_viewers import ViewerDispatcher
from pymodaq_gui.utils import DockArea
from pymodaq_gui.utils.widgets import LabelWithFont
from pymodaq_utils.utils import ThreadCommand


from ..factory import ActuatorUIFactory


@ActuatorUIFactory.register('Original')
class DAQ_Move_UI(DAQ_Move_UI_Base):
    is_compact = False

    def __init__(self, parent, title="DAQ_Move"):
        super().__init__(parent, title)

    def setup_docks(self):
        super().setup_docks()

        self.parent.setLayout(QVBoxLayout())
        #self.parent.layout().setSizeConstraint(QHBoxLayout.SetFixedSize)
        self.parent.layout().setContentsMargins(2, 2, 2, 2)

        widget = QWidget()
        widget.setLayout(QHBoxLayout())
        splitter_hor = QtWidgets.QSplitter(Qt.Orientation.Horizontal)
        widget.layout().addWidget(splitter_hor)
        self.parent.layout().addWidget(widget)

        self.main_ui = QWidget()

        self.control_widget = QWidget()
        self.populate_control_ui(self.control_widget)

        self.settings_ui = QWidget()


        left_widget = QWidget()
        left_widget.setLayout(QVBoxLayout())
        left_widget.layout().addWidget(self.main_ui)
        left_widget.layout().addWidget(self.control_widget)
        left_widget.layout().setContentsMargins(0, 0, 0, 0)
        left_widget.layout().addStretch()
        splitter_hor.addWidget(left_widget)
        splitter_hor.addWidget(self.settings_ui)
        #widget.layout().addStretch()

        # populate the main ui
        self.main_ui.setLayout(QGridLayout())
        self.main_ui.layout().setSpacing(0)
        self.main_ui.layout().setContentsMargins(0, 0, 0, 0)

        self.main_ui.layout().addWidget(self.toolbar, 0, 0, 1, 2)
        self.main_ui.layout().addWidget(self.move_toolbar, 1, 0, 1, 2)


        self.move_toolbar.addWidget(self.abs_value_sb)
        self.move_toolbar.addWidget(self.abs_value_sb_2)

        self.main_ui.layout().addWidget(LabelWithFont('Actuator:'), 2, 0)

        self.main_ui.layout().addWidget(self.actuators_combo, 2, 1)

        self.main_ui.layout().addWidget(self.ini_actuator_pb, 3, 0)
        self.main_ui.layout().addWidget(LabelWithFont('Current value:'), 4, 0)
        self.main_ui.layout().addWidget(self.move_done_led, 4, 1)

        self.main_ui.layout().addWidget(self.current_value_sb, 5, 0, 1, 2)

        self.settings_ui.setLayout(QHBoxLayout())
        self.settings_ui.layout().setContentsMargins(0, 0, 0, 0)
        self.settings_ui.setVisible(False)

        self.statusbar = QtWidgets.QStatusBar()
        self.statusbar.setMaximumHeight(30)
        self.parent.layout().addWidget(self.statusbar)

    def setup_actions(self):
        self.setup_actions_in_toolbar(self.toolbar)

    def connect_things(self):
        super().connect_things()

    def set_settings_tree(self, tree):
        super().set_settings_tree(tree)
        self.settings_ui.layout().addWidget(tree)

    def show_tree(self, show: bool = True):
        super().show_tree(show)
        self.settings_ui.setVisible(show)