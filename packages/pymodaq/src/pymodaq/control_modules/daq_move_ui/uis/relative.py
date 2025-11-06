import sys

from qtpy.QtWidgets import QVBoxLayout, QToolBar
from qtpy import QtWidgets

from pymodaq.control_modules.daq_move_ui.ui_base import DAQ_Move_UI_Base
from pymodaq.control_modules.thread_commands import UiToMainMove
from pymodaq_gui.utils.widgets import LabelWithFont
from pymodaq_utils.utils import ThreadCommand

from pymodaq.control_modules.daq_move_ui.factory import ActuatorUIFactory


@ActuatorUIFactory.register('Relative')
class DAQ_Move_UI_Relative(DAQ_Move_UI_Base):
    is_compact = True
    def __init__(self, parent, title="DAQ_Move"):

        super().__init__(parent, title)

    def setup_docks(self):
        super().setup_docks()

        self.parent.setLayout(QVBoxLayout())
        self.parent.layout().setContentsMargins(0, 0, 0, 0)

        self.move_toolbar = QToolBar()
        self.parent.layout().addWidget(self.move_toolbar)

        self.current_value_sb.set_font_size(10)
        self.current_value_sb.setMinimumHeight(20)
        self.current_value_sb.setMinimumWidth(80)

        self.control_widget = QtWidgets.QWidget()
        self.populate_control_ui(self.control_widget)

    def setup_actions(self):
        self.add_widget('name', LabelWithFont(f'{self.title}', font_name="Tahoma",
                                              font_size=14, isbold=True, isitalic=True),
                        toolbar=self.move_toolbar)

        self.add_widget('actuators_combo', self.actuators_combo, toolbar=self.move_toolbar)
        self.add_action('ini_actuator', 'Ini. Actuator', 'ini', toolbar=self.move_toolbar)
        self.add_widget('ini_led', self.ini_state_led, toolbar=self.move_toolbar)
        self.move_toolbar.addSeparator()
        self.add_widget('current', self.current_value_sb, toolbar=self.move_toolbar)
        self.add_widget('move_done', self.move_done_led, toolbar=self.move_toolbar)
        self.move_toolbar.addSeparator()
        self.add_widget('rel_move', self.rel_value_sb, toolbar=self.move_toolbar)
        self.add_action('move_rel_plus', 'Set Rel. (+)', 'MoveUp', toolbar=self.move_toolbar)
        self.add_action('move_rel_minus', 'Set Rel. (-)', 'MoveDown', toolbar=self.move_toolbar)

        self.add_action('stop', 'Stop', 'stop', "Stop Motion", toolbar=self.move_toolbar)
        self.move_toolbar.addSeparator()
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

        self.connect_action('move_rel_plus', lambda: self.emit_move_rel('+'))
        self.connect_action('move_rel_minus', lambda: self.emit_move_rel('-'))


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
    prog = DAQ_Move_UI_Relative(widget, title="test")
    widget.show()

    for ind in range(10):
        widget = QtWidgets.QWidget()
        widget.setMaximumHeight(60)
        dock.addWidget(widget)
        prog = DAQ_Move_UI_Relative(widget, title="test")


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
