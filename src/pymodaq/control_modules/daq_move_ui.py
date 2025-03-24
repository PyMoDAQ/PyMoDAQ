# -*- coding: utf-8 -*-
"""
Created the 28/07/2022

@author: Sebastien Weber
"""

from typing import List, Union
import sys
from pint.errors import DimensionalityError

from qtpy import QtWidgets
from qtpy.QtCore import Signal, Qt
from qtpy.QtWidgets import QHBoxLayout, QVBoxLayout, QGridLayout, QWidget, QToolBar, QComboBox

from pymodaq_utils.utils import ThreadCommand
from pymodaq_utils.config import Config

from pymodaq_data import Q_

from pymodaq_gui.utils.widgets import PushButtonIcon, LabelWithFont, SpinBox, QSpinBox_ro, QLED, QSpinBoxWithShortcut
from pymodaq_gui.utils import DockArea
from pymodaq_gui.plotting.data_viewers.viewer import ViewerDispatcher

from pymodaq.control_modules.utils import ControlModuleUI
from pymodaq.utils.data import DataToExport, DataActuator
from pymodaq.control_modules.thread_commands import UiToMainMove

config = Config()

class DAQ_Move_UI_Base(ControlModuleUI):
    """DAQ_Move user interface.

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
            * show_config
            * show_plugin_config

    Methods
    -------
    display_value(value: float)
        Update the display of the actuator's value on the UI
    do_init()
        Programmatic init

    See Also
    --------
    pymodaq.utils.daq_utils.ThreadCommand
    """

    def __init__(self, parent: Union[DockArea, QtWidgets.QWidget], title="DAQ_Move"):
        super().__init__(parent)
        self.title = title
        self._unit = ''

        self.actuators_combo: QComboBox = None
        self.abs_value_sb: QSpinBoxWithShortcut = None
        self.abs_value_sb_2: QSpinBoxWithShortcut = None
        self.abs_value_sb_bis: QSpinBoxWithShortcut = None
        self.ini_actuator_pb: PushButtonIcon = None
        self.ini_state_led: QLED = None
        self.move_done_led: QLED = None
        self.current_value_sb: QSpinBox_ro = None
        self.find_home_pb: PushButtonIcon = None
        self.move_rel_plus_pb: PushButtonIcon = None
        self.move_abs_pb: PushButtonIcon = None
        self.rel_value_sb: QSpinBoxWithShortcut = None
        self.move_rel_minus_pb: PushButtonIcon = None
        self.stop_pb: PushButtonIcon = None
        self.get_value_pb: PushButtonIcon = None
        self.statusbar: QtWidgets.QStatusBar = None


        self.setup_ui()

        self.enable_move_buttons(False)

    def display_value(self, value: DataActuator):
        try:
            self.current_value_sb.setValue(value.value(self._unit))
        except DimensionalityError as e:
            value.force_units(self._unit)
            self.current_value_sb.setValue(value.value())

    @property
    def actuator_init(self):
        """bool: the status of the init LED."""
        return self.ini_state_led.get_state()

    @actuator_init.setter
    def actuator_init(self, status):
        self.ini_state_led.set_as(status)
        self.enable_move_buttons(status)

    @property
    def actuator(self):
        return self.actuators_combo.currentText()

    @actuator.setter
    def actuator(self, act_name: str):
        self.actuators_combo.setCurrentText(act_name)

    @property
    def actuators(self):
        return [self.actuators_combo.itemText(ind) for ind in range(self.actuators_combo.count())]

    @actuators.setter
    def actuators(self, actuators: List[str]):
        self.actuators_combo.clear()
        self.actuators_combo.addItems(actuators)

    @property
    def move_done(self):
        """bool: the status of the move_done LED."""
        return self.move_done_led.get_state()

    @move_done.setter
    def move_done(self, status):
        self.move_done_led.set_as(status)

    def enable_move_buttons(self, status):
        self.abs_value_sb.setEnabled(status)
        self.abs_value_sb_2.setEnabled(status)

        self.get_action('move_abs').setEnabled(status)
        self.get_action('move_abs_2').setEnabled(status)

    def set_abs_spinbox_properties(self, **properties):
        """ Change the Spinbox properties

        Parameters
        --------
        properties: dict or named parameters
            possible keys are :

            * decimals: to set the number of displayed decimals
            * 'minimum': to set the minimum value
            * 'maximum': to set the maximum value
            * 'step': to set the step value

        """
        if 'decimals' in properties:
            self.abs_value_sb.setDecimals(properties['decimals'])
            self.abs_value_sb_2.setDecimals(properties['decimals'])
            self.abs_value_sb_bis.setDecimals(properties['decimals'])
        if 'minimum' in properties:
            self.abs_value_sb.setMinimum(properties['minimum'])
            self.abs_value_sb_2.setMinimum(properties['minimum'])
            self.abs_value_sb_bis.setMinimum(properties['minimum'])
        if 'maximum' in properties:
            self.abs_value_sb.setMaximum(properties['maximum'])
            self.abs_value_sb_2.setMaximum(properties['maximum'])
            self.abs_value_sb_bis.setMaximum(properties['maximum'])
        if 'step' in properties:
            self.abs_value_sb.setSingleStep(properties['step'])
            self.abs_value_sb_2.setSingleStep(properties['step'])
            self.abs_value_sb_bis.setSingleStep(properties['step'])

    def set_abs_value_red(self, value: Q_):
        self.abs_value_sb_2.setValue(value.m_as(self._unit))

    def set_abs_value_green(self, value: Q_):
        self.abs_value_sb.setValue(value.m_as(self._unit))

    def set_abs_value(self, value: Q_):
        self.abs_value_sb_bis.setValue(value.m_as(self._unit))

    def set_rel_value(self, value: Q_):
        self.rel_value_sb.setValue(value.m_as(self._unit))

    def set_unit_as_suffix(self, unit: str):
        """Will append the actuator units in the value display"""
        self._unit = unit
        self.current_value_sb.setOpts(suffix=unit)
        self.abs_value_sb_bis.setOpts(suffix=unit)
        self.abs_value_sb.setOpts(suffix=unit)
        self.abs_value_sb_2.setOpts(suffix=unit)
        self.rel_value_sb.setOpts(suffix=unit)

    def setup_docks(self):
        self.actuators_combo = QComboBox()
        self.abs_value_sb = QSpinBoxWithShortcut(step=0.1, dec=True, siPrefix=config('actuator', 'siprefix'))
        self.abs_value_sb.setStyleSheet("background-color : lightgreen; color: black")

        self.abs_value_sb_2 = QSpinBoxWithShortcut(step=0.1, dec=True, siPrefix=config('actuator', 'siprefix'))
        self.abs_value_sb_2.setStyleSheet("background-color : lightcoral; color: black")

        self.abs_value_sb_bis = QSpinBoxWithShortcut(step=0.1, dec=True, siPrefix=config('actuator', 'siprefix'))
        self.ini_actuator_pb = PushButtonIcon('ini', 'Initialization', checkable=True,
                                              tip='Start This actuator initialization')
        self.ini_state_led = QLED(readonly=True)
        self.move_done_led = QLED(readonly=True)
        self.current_value_sb = QSpinBox_ro(font_size=20, min_height=27,
                                            siPrefix=config('actuator', 'siprefix'),
                                            )
        self.find_home_pb = PushButtonIcon('home2', 'Find Home')
        self.move_rel_plus_pb = PushButtonIcon('MoveUp', 'Set Rel. (+)')
        self.move_abs_pb = PushButtonIcon('Move', 'Set Abs.',
                                          tip='Set the value of the actuator to the set absolute value')
        self.rel_value_sb = QSpinBoxWithShortcut(step=0.1, dec=True, siPrefix=config('actuator', 'siprefix'),
                                                 key_sequences=("Ctrl+E","Ctrl+Shift+E"),)
        self.move_rel_minus_pb = PushButtonIcon('MoveDown', 'Set Rel. (-)')
        self.stop_pb = PushButtonIcon('stop', 'Stop')
        self.get_value_pb = PushButtonIcon('Help_32', 'Update Value')
        self.statusbar = QtWidgets.QStatusBar()
        self.statusbar.setMaximumHeight(30)

    def close(self):
        self.parent.close()

    def do_init(self, do_init=True):
        """Programmatically press the Init button
        API entry
        Parameters
        ----------
        do_init: bool
            will fire the Init button depending on the argument value and the button check state
        """
        if do_init is not self.ini_actuator_pb.isChecked():
            self.ini_actuator_pb.click()

    def send_init(self, checked):
        self.actuators_combo.setEnabled(not checked)
        self.command_sig.emit(ThreadCommand(UiToMainMove.INIT, [self.ini_actuator_pb.isChecked(),
                                                                self.actuators_combo.currentText()]))

    def emit_move_abs(self, spinbox):
        spinbox.editingFinished.emit()
        self.command_sig.emit(ThreadCommand(UiToMainMove.MOVE_ABS, DataActuator(data=spinbox.value(),
                                                                                units=self._unit)))

    def emit_move_rel(self, sign):
        self.command_sig.emit(ThreadCommand(
            UiToMainMove.MOVE_REL,
            DataActuator(data=self.rel_value_sb.value() * (1 if sign == '+' else -1),
                         units=self._unit)))

    def set_settings_tree(self, tree):
        self.settings_ui.layout().addWidget(tree)


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


class DAQ_Move_UI_Simple(DAQ_Move_UI_Base):
    def __init__(self, parent, title="DAQ_Move"):

        super().__init__(parent, title)

    def setup_docks(self):
        super().setup_docks()

        self.parent.setLayout(QVBoxLayout())
        self.parent.layout().setContentsMargins(0, 0, 0, 0)

        self.move_toolbar = QToolBar()
        self.parent.layout().addWidget(self.move_toolbar)

        self.abs_value_sb_2.setMinimumWidth(80)
        self.abs_value_sb.setMinimumWidth(80)
        self.current_value_sb.set_font_size(10)
        self.current_value_sb.setMinimumHeight(20)


    def setup_actions(self):
        self.add_widget('name', LabelWithFont(f'{self.title}: ', font_name="Tahoma",
                                              font_size=14, isbold=True, isitalic=True),
                        toolbar=self.move_toolbar)

        self.add_widget('actuators_combo', self.actuators_combo, toolbar=self.move_toolbar)
        self.add_action('ini_actuator', 'Ini. Actuator', 'ini', toolbar=self.move_toolbar)
        self.add_widget('ini_led', self.ini_state_led, toolbar=self.move_toolbar)
        self.add_widget('abs_green', self.abs_value_sb, toolbar=self.move_toolbar)
        self.add_widget('abs_red', self.abs_value_sb_2, toolbar=self.move_toolbar)
        self.add_action('move_abs', 'Move Abs', 'go_to_1', "Move to the set absolute value",
                        toolbar=self.move_toolbar)
        self.add_action('move_abs_2', 'Move Abs', 'go_to_2', "Move to the other set absolute"
                                                             " value",
                        toolbar=self.move_toolbar)
        self.add_widget('move_done', self.move_done_led, toolbar=self.move_toolbar)
        self.add_widget('current', self.current_value_sb, toolbar=self.move_toolbar)

        self.add_action('stop', 'Stop', 'stop', "Stop Motion", toolbar=self.move_toolbar)

        self.add_action('quit', 'Quit the module', 'close2', toolbar=self.move_toolbar)
        self.add_action('log', 'Show Log file', 'information2', toolbar=self.move_toolbar)

        self.add_widget('status', self.statusbar, toolbar=self.move_toolbar)

    def connect_things(self):
        self.connect_action('ini_actuator', self.ini_actuator_pb.click)

        self.connect_action('quit', lambda: self.command_sig.emit(ThreadCommand(UiToMainMove.QUIT, )))

        self.connect_action('move_abs', lambda: self.emit_move_abs(self.abs_value_sb))
        self.connect_action('move_abs_2', lambda: self.emit_move_abs(self.abs_value_sb_2))
        self.connect_action('log', lambda: self.command_sig.emit(ThreadCommand(UiToMainMove.SHOW_LOG, )))
        self.connect_action('stop', lambda: self.command_sig.emit(ThreadCommand(UiToMainMove.STOP, )))

        self.move_abs_pb.clicked.connect(lambda: self.emit_move_abs(self.abs_value_sb_bis))
        self.abs_value_sb.shortcut["Ctrl+E"].activated.connect(lambda: self.emit_move_abs(self.abs_value_sb))
        self.abs_value_sb_2.shortcut["Ctrl+E"].activated.connect(lambda: self.emit_move_abs(self.abs_value_sb_2))


        self.ini_actuator_pb.clicked.connect(self.send_init)

        self.actuators_combo.currentTextChanged.connect(
            lambda act: self.command_sig.emit(ThreadCommand(UiToMainMove.ACTUATOR_CHANGED, act)))



def main(init_qt=True):
    from pymodaq_gui.utils.dock import DockArea, Dock
    if init_qt:  # used for the test suite
        app = QtWidgets.QApplication(sys.argv)

    actuators = [f'act{ind}' for ind in range(5)]

    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('extension_name')


    dock = Dock('Test')
    dock.layout.setSpacing(0)
    dock.layout.setContentsMargins(0,0,0,0)
    area.addDock(dock)
    widget = QtWidgets.QWidget()
    widget.setMaximumHeight(60)
    prog = DAQ_Move_UI_Simple(widget, title="test")
    widget.show()

    for ind in range(10):
        widget = QtWidgets.QWidget()
        widget.setMaximumHeight(60)
        dock.addWidget(widget)
        prog = DAQ_Move_UI_Simple(widget, title="test")


        def print_command_sig(cmd_sig):
            print(cmd_sig)
            if cmd_sig.command == UiToMainMove.INIT:
                prog.enable_move_buttons(True)
            elif cmd_sig.command == UiToMainMove.MOVE_ABS:
                prog.display_value(cmd_sig.attribute)

        prog.command_sig.connect(print_command_sig)
        prog.actuators = actuators

    win.show()
    if init_qt:
        sys.exit(app.exec_())
    return prog, widget


if __name__ == '__main__':
    main()
