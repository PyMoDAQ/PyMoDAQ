# -*- coding: utf-8 -*-
"""
Created the 28/07/2022

@author: Sebastien Weber
"""

from typing import List
import sys

from qtpy import QtWidgets
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QHBoxLayout, QVBoxLayout, QGridLayout, QWidget, QToolBar, QComboBox

from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.gui_utils.custom_app import CustomApp
from pymodaq.utils.gui_utils.widgets import PushButtonIcon, LabelWithFont, SpinBox, QSpinBox_ro, QLED
from pymodaq.control_modules.utils import ControlModuleUI
from pymodaq.utils.gui_utils import DockArea
from pymodaq.utils.plotting.data_viewers.viewer import ViewerDispatcher
from pymodaq.utils.data import DataWithAxes, DataToExport, DataActuator


class DAQ_Move_UI(ControlModuleUI):
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

    def __init__(self, parent, title="DAQ_Move"):

        super().__init__(parent)
        self.title = title
        self.setup_ui()

        self.enable_move_buttons(False)

    def display_value(self, value: DataActuator):
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

    def set_settings_tree(self, tree):
        self.settings_ui.layout().addWidget(tree)

    def enable_move_buttons(self, status):
        self.abs_value_sb.setEnabled(status)
        self.abs_value_sb_2.setEnabled(status)
        self.control_ui.setEnabled(status)

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

    def show_data(self, data: DataToExport):
        self.viewer.show_data(data)

    def setup_docks(self):
        self.parent.setLayout(QVBoxLayout())
        self.parent.layout().setSizeConstraint(QHBoxLayout.SetFixedSize)
        self.parent.layout().setContentsMargins(2, 2, 2, 2)

        widget = QWidget()
        widget.setLayout(QHBoxLayout())
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
        widget.layout().addWidget(left_widget)
        widget.layout().addWidget(self.settings_ui)
        widget.layout().addStretch()

        # populate the main ui
        self.move_toolbar = QToolBar()
        self.main_ui.setLayout(QGridLayout())
        self.main_ui.layout().setSpacing(0)
        self.main_ui.layout().setContentsMargins(0, 0, 0, 0)

        self.main_ui.layout().addWidget(self.toolbar, 0, 0, 1, 2)
        self.main_ui.layout().addWidget(self.move_toolbar, 1, 0, 1, 2)

        self.abs_value_sb = SpinBox()
        self.abs_value_sb.setStyleSheet("background-color : lightgreen; color: black")
        self.abs_value_sb_2 = SpinBox()
        self.abs_value_sb_2.setStyleSheet("background-color : lightcoral; color: black")
        self.move_toolbar.addWidget(self.abs_value_sb)
        self.move_toolbar.addWidget(self.abs_value_sb_2)

        self.main_ui.layout().addWidget(LabelWithFont('Actuator:'), 2, 0)
        self.actuators_combo = QComboBox()
        self.main_ui.layout().addWidget(self.actuators_combo, 2, 1)
        self.ini_actuator_pb = PushButtonIcon('ini', 'Initialization', checkable=True,
                                           tip='Start This actuator initialization')
        self.main_ui.layout().addWidget(self.ini_actuator_pb, 3, 0)
        self.ini_state_led = QLED(readonly=True)
        self.main_ui.layout().addWidget(self.ini_state_led, 3, 1)
        self.main_ui.layout().addWidget(LabelWithFont('Current value:'), 4, 0)
        self.move_done_led = QLED(readonly=True)
        self.main_ui.layout().addWidget(self.move_done_led, 4, 1)
        self.current_value_sb = QSpinBox_ro(font_size=30, min_height=35)
        self.main_ui.layout().addWidget(self.current_value_sb, 5, 0, 1, 2)

        # populate the control ui
        self.control_ui.setLayout(QGridLayout())
        self.control_ui.layout().addWidget(LabelWithFont('Abs. Value'), 0, 0)
        self.find_home_pb = PushButtonIcon('home2', 'Find Home')
        self.control_ui.layout().addWidget(self.find_home_pb, 0, 1)
        self.abs_value_sb_bis = SpinBox()
        self.control_ui.layout().addWidget(self.abs_value_sb_bis, 1, 0)
        self.move_abs_pb = PushButtonIcon('Move', 'Set Abs.',
                                          tip='Set the value of the actuator to the set absolute value')
        self.control_ui.layout().addWidget(self.move_abs_pb, 1, 1)
        self.control_ui.layout().addWidget(LabelWithFont('Rel. Increment'), 2, 0)
        self.move_rel_plus_pb = PushButtonIcon('MoveUp', 'Set Rel. (+)')
        self.control_ui.layout().addWidget(self.move_rel_plus_pb, 2, 1)

        self.rel_value_sb = SpinBox()
        self.control_ui.layout().addWidget(self.rel_value_sb, 3, 0)
        self.move_rel_minus_pb = PushButtonIcon('MoveDown', 'Set Rel. (-)')
        self.control_ui.layout().addWidget(self.move_rel_minus_pb, 3, 1)
        self.stop_pb = PushButtonIcon('stop', 'Stop')
        self.control_ui.layout().addWidget(self.stop_pb, 4, 0)
        self.get_value_pb = PushButtonIcon('Help_32', 'Update Value')
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

        self.connect_action('quit', lambda: self.command_sig.emit(ThreadCommand('quit', )))
        self.connect_action('refresh_value',
                            lambda do_refresh: self.command_sig.emit(ThreadCommand('loop_get_value', do_refresh)))
        self.connect_action('move_abs', lambda: self.emit_move_abs(self.abs_value_sb))
        self.connect_action('move_abs_2', lambda: self.emit_move_abs(self.abs_value_sb_2))
        self.connect_action('log', lambda: self.command_sig.emit(ThreadCommand('show_log', )))
        self.connect_action('stop', lambda: self.command_sig.emit(ThreadCommand('stop', )))
        self.connect_action('show_config', lambda: self.command_sig.emit(ThreadCommand('show_config', )))

        self.move_abs_pb.clicked.connect(lambda: self.emit_move_abs(self.abs_value_sb_bis))

        self.rel_value_sb.valueChanged.connect(lambda: self.command_sig.emit(
            ThreadCommand('rel_value', self.rel_value_sb.value())))
        self.move_rel_plus_pb.clicked.connect(lambda: self.emit_move_rel('+'))
        self.move_rel_minus_pb.clicked.connect(lambda: self.emit_move_rel('-'))

        self.find_home_pb.clicked.connect(lambda: self.command_sig.emit(ThreadCommand('find_home', )))
        self.stop_pb.clicked.connect(lambda: self.command_sig.emit(ThreadCommand('stop', )))
        self.get_value_pb.clicked.connect(lambda: self.command_sig.emit(ThreadCommand('get_value', )))

        self.ini_actuator_pb.clicked.connect(self.send_init)

        self.actuators_combo.currentTextChanged.connect(
            lambda act: self.command_sig.emit(ThreadCommand('actuator_changed', act)))

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
        self.command_sig.emit(ThreadCommand('init', [self.ini_actuator_pb.isChecked(),
                                                     self.actuators_combo.currentText()]))

    def emit_move_abs(self, spinbox):
        self.command_sig.emit(ThreadCommand('move_abs', DataActuator(data=spinbox.value())))

    def emit_move_rel(self, sign):
        self.command_sig.emit(ThreadCommand('move_rel',
                                            DataActuator(data=self.rel_value_sb.value() * (1 if sign == '+'
                                                                                           else -1))))

    def close(self):
        self.graph_ui.close()
        self.parent.close()


def main(init_qt=True):
    from pymodaq.utils.gui_utils.dock import DockArea
    if init_qt:  # used for the test suite
        app = QtWidgets.QApplication(sys.argv)

    actuators = [f'act{ind}' for ind in range(5)]

    widget = QtWidgets.QWidget()
    prog = DAQ_Move_UI(widget, title="test")
    widget.show()
    
    def print_command_sig(cmd_sig):
        print(cmd_sig)
        if cmd_sig.command == 'init':
            prog.enable_move_buttons(True)
        
    prog.command_sig.connect(print_command_sig)
    prog.actuators = actuators


            
    if init_qt:
        sys.exit(app.exec_())
    return prog, widget


if __name__ == '__main__':
    main()
