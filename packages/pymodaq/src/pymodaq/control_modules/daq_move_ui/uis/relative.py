import sys

from qtpy.QtWidgets import QVBoxLayout, QToolBar
from qtpy import QtWidgets
import qt_themes

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

    def setup_docks_and_widgets(self):
        super().setup_docks_and_widgets()

        self.parent.setLayout(QVBoxLayout())
        self.parent.layout().setContentsMargins(0, 0, 0, 0)

        self.parent.layout().addWidget(self.toolbar)

        self.current_value_sb.set_font_size(10)
        self.current_value_sb.setMinimumHeight(20)
        self.current_value_sb.setMinimumWidth(80)

        self.control_widget = QtWidgets.QWidget()
        self.populate_control_ui(self.control_widget)

    def setup_actions(self):
        self.setup_actions_in_toolbar(self.move_toolbar)

    def _setup_move_actions(self, toolbar: QtWidgets.QToolBar):
        self._setup_relative_actions(toolbar)

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
        sys.exit(app.exec())
    return prog, widget


if __name__ == '__main__':
    main()
