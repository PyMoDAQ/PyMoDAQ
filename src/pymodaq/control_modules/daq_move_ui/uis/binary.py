import sys
from typing import Union

from qtpy.QtWidgets import QVBoxLayout, QToolBar
from qtpy import QtWidgets

from pymodaq.control_modules.daq_move_ui.ui_base import DAQ_Move_UI_Base
from pymodaq.control_modules.thread_commands import UiToMainMove
from pymodaq_gui.utils.widgets import LabelWithFont

from pymodaq.utils.data import DataActuator

from pymodaq_utils.utils import ThreadCommand
from pymodaq_utils.config import Config

from pymodaq.control_modules.daq_move_ui.factory import ActuatorUIFactory
from pymodaq.control_modules.daq_move_ui.uis.simple import DAQ_Move_UI_Simple
from pymodaq.utils.config import Config as ControlModulesConfig
from enum import Enum

config = ControlModulesConfig()


class BinaryValue(Enum):
    VALUE_ONE = config('actuator', 'binary', 'value_1')
    VALUE_TWO = config('actuator', 'binary', 'value_2')


@ActuatorUIFactory.register('Binary')
class DAQ_Move_UI_Binary(DAQ_Move_UI_Simple):
    """ UI for Actuators where only two values are encoded: 0 or 1 for instance

    Some other numerical values can be set in the config: 'actuator', 'binary', 'value_1'
    The green arrow button will fire the 'value_1'
    The red arrow button will fire the 'value_2'

    Could be used for 2 positions only actuators such as a Flip
    """


    is_compact = True

    def setup_actions(self):
        self.add_widget('name', LabelWithFont(f'{self.title}: ', font_name="Tahoma",
                                              font_size=14, isbold=True, isitalic=True),
                        toolbar=self.move_toolbar)

        self.add_widget('actuators_combo', self.actuators_combo, toolbar=self.move_toolbar)
        self.add_action('ini_actuator', 'Ini. Actuator', 'ini', toolbar=self.move_toolbar)
        self.add_widget('ini_led', self.ini_state_led, toolbar=self.move_toolbar)
        self.add_widget('current', self.current_value_sb, toolbar=self.move_toolbar)
        self.add_widget('move_done', self.move_done_led, toolbar=self.move_toolbar)
        self.add_action('move_abs', 'Move Abs', 'go_to_1', "Move to the set absolute value",
                        toolbar=self.move_toolbar)
        self.add_action('move_abs_2', 'Move Abs', 'go_to_2', "Move to the other set absolute"
                                                             " value",
                        toolbar=self.move_toolbar)


        self.add_action('stop', 'Stop', 'stop', "Stop Motion", toolbar=self.move_toolbar)

        self.add_action('show_settings', 'Show Settings', 'tree', "Show Settings", checkable=True,
                        toolbar=self.move_toolbar)
        self.add_action('show_controls', 'Show Controls', 'Add_Step', "Show more controls", checkable=True,
                        toolbar=self.move_toolbar)
        self.add_action('show_graph', 'Show Graph', 'graph', "Show Graph", checkable=True,
                        toolbar=self.move_toolbar)
        self.add_action('refresh_value', 'Refresh', 'Refresh2', "Refresh Value", checkable=True,
                        toolbar=self.move_toolbar)
        self.move_toolbar.addSeparator()
        self.add_action('show_config', 'Show Config', 'Settings', "Show PyMoDAQ Config", checkable=False,
                        toolbar=self.move_toolbar)
        self.add_action('quit', 'Quit the module', 'close2', toolbar=self.move_toolbar)
        self.add_action('log', 'Show Log file', 'information2', toolbar=self.move_toolbar)
        self.add_widget('status', self.statusbar, toolbar=self.move_toolbar)

    def connect_things(self):
        super().connect_things()
        # first disconnect actions from  the base class
        self.connect_action('move_abs', None, connect=False)
        self.connect_action('move_abs_2', None, connect=False)

        #then connect to the ones reimplemented here
        self.connect_action('move_abs', lambda: self.emit_move_abs(BinaryValue.VALUE_ONE.value))
        self.connect_action('move_abs_2', lambda: self.emit_move_abs(BinaryValue.VALUE_TWO.value))

    def emit_move_abs(self, abs_value: Union[float, int]):
        self.command_sig.emit(ThreadCommand(UiToMainMove.MOVE_ABS, DataActuator(data=abs_value,
                                                                                units=self._unit)))

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
        prog = DAQ_Move_UI_Binary(widget, title="test")


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

