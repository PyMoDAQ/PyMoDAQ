from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QToolBar, QGridLayout
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
    def __init__(self, parent, title="DAQ_Move"):
        super().__init__(parent, title)

    def enable_move_buttons(self, status):
        super().enable_move_buttons(status)
        self.control_ui.setEnabled(status)

    def show_data(self, data: DataToExport):
        self.viewer.show_data(data)

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
        self.control_ui = QWidget()
        self.settings_ui = QWidget()
        self.graph_ui = QWidget()
        self.graph_ui.setLayout(QtWidgets.QHBoxLayout())
        self.graph_ui.layout().setContentsMargins(0, 0, 0, 0)
        dockarea = DockArea()
        self.graph_ui.layout().addWidget(dockarea)
        self.viewer = ViewerDispatcher(dockarea)

        left_widget = QWidget()
        left_widget.setLayout(QVBoxLayout())
        left_widget.layout().addWidget(self.main_ui)
        left_widget.layout().addWidget(self.control_ui)
        left_widget.layout().setContentsMargins(0, 0, 0, 0)
        left_widget.layout().addStretch()
        splitter_hor.addWidget(left_widget)
        splitter_hor.addWidget(self.settings_ui)
        #widget.layout().addStretch()

        # populate the main ui
        self.move_toolbar = QToolBar()
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
        self.main_ui.layout().addWidget(self.ini_state_led, 3, 1)
        self.main_ui.layout().addWidget(LabelWithFont('Current value:'), 4, 0)
        self.main_ui.layout().addWidget(self.move_done_led, 4, 1)

        self.main_ui.layout().addWidget(self.current_value_sb, 5, 0, 1, 2)

        # populate the control ui
        self.control_ui.setLayout(QGridLayout())
        self.control_ui.layout().addWidget(LabelWithFont('Abs. Value'), 0, 0)

        self.control_ui.layout().addWidget(self.find_home_pb, 0, 1)

        self.control_ui.layout().addWidget(self.abs_value_sb_bis, 1, 0)
        self.control_ui.layout().addWidget(self.move_abs_pb, 1, 1)
        self.control_ui.layout().addWidget(LabelWithFont('Rel. Increment'), 2, 0)
        self.control_ui.layout().addWidget(self.move_rel_plus_pb, 2, 1)

        self.control_ui.layout().addWidget(self.rel_value_sb, 3, 0)

        self.control_ui.layout().addWidget(self.move_rel_minus_pb, 3, 1)
        self.control_ui.layout().addWidget(self.stop_pb, 4, 0)

        self.control_ui.layout().addWidget(self.get_value_pb, 4, 1)
        self.control_ui.layout().setContentsMargins(0, 0, 0, 0)

        self.settings_ui.setLayout(QHBoxLayout())
        self.settings_ui.layout().setContentsMargins(0, 0, 0, 0)

        self.control_ui.setVisible(False)
        self.settings_ui.setVisible(False)

        self.statusbar = QtWidgets.QStatusBar()
        self.statusbar.setMaximumHeight(30)
        self.parent.layout().addWidget(self.statusbar)

    def setup_actions(self):
        self.add_action('move_abs', 'Move Abs', 'go_to_1', "Move to the set absolute value",
                        toolbar=self.move_toolbar)
        self.add_action('move_abs_2', 'Move Abs', 'go_to_2', "Move to the other set absolute value",
                        toolbar=self.move_toolbar)
        self.add_action('show_controls', 'Show Controls', 'Add_Step', "Show more controls", checkable=True,
                        toolbar=self.toolbar)
        self.add_action('show_settings', 'Show Settings', 'tree', "Show Settings", checkable=True,
                        toolbar=self.toolbar)
        self.add_action('show_config', 'Show Config', 'Settings', "Show PyMoDAQ Config", checkable=False,
                        toolbar=self.toolbar)
        self.add_action('show_graph', 'Show Graph', 'graph', "Show Graph", checkable=True,
                        toolbar=self.toolbar)
        self.add_action('refresh_value', 'Refresh', 'Refresh2', "Refresh Value", checkable=True,
                        toolbar=self.toolbar)
        self.add_action('stop', 'Stop', 'stop', "Stop Motion", checkable=False,
                        toolbar=self.toolbar)
        self.add_action('quit', 'Quit the module', 'close2')
        self.add_action('log', 'Show Log file', 'information2')

        self.toolbar.addWidget(LabelWithFont(self.title, font_name="Tahoma", font_size=14, isbold=True, isitalic=True))

    def connect_things(self):
        self.connect_action('show_controls', lambda show: self.control_ui.setVisible(show))
        self.connect_action('show_settings', lambda show: self.settings_ui.setVisible(show))
        self.connect_action('show_graph', lambda show: self.graph_ui.setVisible(show))

        self.connect_action('quit', lambda: self.command_sig.emit(ThreadCommand(UiToMainMove.QUIT, )))
        self.connect_action('refresh_value',
                            lambda do_refresh: self.command_sig.emit(ThreadCommand(UiToMainMove.LOOP_GET_VALUE,
                                                                                   do_refresh)))
        self.connect_action('move_abs', lambda: self.emit_move_abs(self.abs_value_sb))
        self.connect_action('move_abs_2', lambda: self.emit_move_abs(self.abs_value_sb_2))
        self.connect_action('log', lambda: self.command_sig.emit(ThreadCommand(UiToMainMove.SHOW_LOG, )))
        self.connect_action('stop', lambda: self.command_sig.emit(ThreadCommand(UiToMainMove.STOP, )))
        self.connect_action('show_config', lambda: self.command_sig.emit(ThreadCommand(UiToMainMove.SHOW_CONFIG, )))

        self.move_abs_pb.clicked.connect(lambda: self.emit_move_abs(self.abs_value_sb_bis))
        self.abs_value_sb.shortcut["Ctrl+E"].activated.connect(lambda: self.emit_move_abs(self.abs_value_sb))
        self.abs_value_sb_2.shortcut["Ctrl+E"].activated.connect(lambda: self.emit_move_abs(self.abs_value_sb_2))
        self.abs_value_sb_bis.shortcut["Ctrl+E"].activated.connect(lambda: self.emit_move_abs(self.abs_value_sb_bis))


        self.rel_value_sb.valueChanged.connect(lambda: self.command_sig.emit(
            ThreadCommand(UiToMainMove.REL_VALUE, self.rel_value_sb.value())))
        self.move_rel_plus_pb.clicked.connect(lambda: self.emit_move_rel('+'))
        self.move_rel_minus_pb.clicked.connect(lambda: self.emit_move_rel('-'))
        self.rel_value_sb.shortcut["Ctrl+E"].activated.connect(lambda: self.emit_move_rel('+'))
        self.rel_value_sb.shortcut["Ctrl+Shift+E"].activated.connect(lambda: self.emit_move_rel('-'))

        self.find_home_pb.clicked.connect(lambda: self.command_sig.emit(ThreadCommand(UiToMainMove.FIND_HOME, )))
        self.stop_pb.clicked.connect(lambda: self.command_sig.emit(ThreadCommand(UiToMainMove.STOP, )))
        self.get_value_pb.clicked.connect(lambda: self.command_sig.emit(ThreadCommand(UiToMainMove.GET_VALUE, )))

        self.ini_actuator_pb.clicked.connect(self.send_init)

        self.actuators_combo.currentTextChanged.connect(
            lambda act: self.command_sig.emit(ThreadCommand(UiToMainMove.ACTUATOR_CHANGED, act)))


    def close(self):
        super().close()
        self.graph_ui.close()

    def set_settings_tree(self, tree):
        self.settings_ui.layout().addWidget(tree)
