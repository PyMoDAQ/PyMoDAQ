# -*- coding: utf-8 -*-
"""
Created the 06/12/2022

@author: Sebastien Weber
"""
import sys
from typing import List, TYPE_CHECKING

from qtpy import QtWidgets, QtCore
from qtpy.QtCore import Signal

from pymodaq_utils.utils import ThreadCommand
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.config import Config

from pymodaq_gui.utils import CustomApp
from pymodaq_gui.utils import DockArea, Dock
from pymodaq_gui.utils.widgets.spinbox import QSpinBox_ro
from pymodaq_gui.utils.widgets import QLED
from pymodaq_gui.plotting.data_viewers.viewer import ViewerDispatcher
from pymodaq_gui.plotting.data_viewers import ViewersEnum


if TYPE_CHECKING:
    from pymodaq.utils.parameter import ParameterTree

config = Config()
logger = set_logger(get_module_name(__file__))


class DAQScanUI(CustomApp, ViewerDispatcher):
    """

    """
    command_sig = Signal(ThreadCommand)

    def __init__(self, parent):
        CustomApp.__init__(self, parent)
        self.setup_docks()
        ViewerDispatcher.__init__(self, self.dockarea, title='Scanner',
                                  next_to_dock=self.dock_command)

        self.setup_menu(self._menubar)
        self.setup_actions()
        self.connect_things()

    def setup_actions(self):
        self.add_action('quit', 'Quit the module', 'close2', menu=self.file_menu)
        self.add_action('ini_positions', 'Init Positions', '', menu=self.action_menu)
        self.add_action('start', 'Start Scan', 'run2', "Start the scan", menu=self.action_menu)
        self.add_action('start_batch', 'Start ScanBatches', 'run_all', "Start the batch of scans", menu=self.action_menu)
        self.add_action('stop', 'Stop Scan', 'stop', "Stop the scan", menu=self.action_menu)
        self.add_action('move_at', 'Move at doubleClicked', 'move_contour',
                        "Move to positions where you double clicked", checkable=True, menu=self.action_menu)
        self.add_action('log', 'Show Log file', 'information2', menu=self.file_menu)

        self.add_action('load', 'Load File', 'Open', menu=self.file_menu, auto_toolbar=False)
        self.file_menu.addSeparator()
        self.add_action('save', 'Save file as', 'SaveAs', menu=self.file_menu, auto_toolbar=False)
        self.add_action('show_file', 'Show file content', '', menu=self.file_menu, auto_toolbar=False)

        self.add_action('navigator', 'Show Navigator', '', menu=self._extensions_menu, auto_toolbar=False)
        self.add_action('batch', 'Show Batch Scanner', '', menu=self._extensions_menu, auto_toolbar=False)
        self.set_action_visible('start_batch', False)

    def enable_start_stop(self, enable=True):
        """If True enable main buttons to launch/stop scan"""
        self.set_action_enabled('start', enable)
        self.set_action_enabled('stop', enable)

    def connect_things(self):
        self.connect_action('quit', lambda: self.command_sig.emit(ThreadCommand('quit')))
        self.connect_action('ini_positions', lambda: self.command_sig.emit(ThreadCommand('ini_positions')))
        self.connect_action('start', lambda: self.command_sig.emit(ThreadCommand('start')))
        self.connect_action('start_batch', lambda: self.command_sig.emit(ThreadCommand('start_batch')))
        self.connect_action('stop', lambda: self.command_sig.emit(ThreadCommand('stop')))
        self.connect_action('move_at', lambda: self.command_sig.emit(ThreadCommand('move_at')))
        self.connect_action('log', lambda: self.command_sig.emit(ThreadCommand('show_log', )))

        self.connect_action('load', lambda: self.command_sig.emit(ThreadCommand('load')))
        self.connect_action('save', lambda: self.command_sig.emit(ThreadCommand('save')))
        self.connect_action('show_file', lambda: self.command_sig.emit(ThreadCommand('show_file')))
        self.connect_action('navigator', lambda: self.command_sig.emit(ThreadCommand('navigator')))
        self.connect_action('batch', lambda: self.command_sig.emit(ThreadCommand('batch')))

    def setup_menu(self, menubar: QtWidgets.QMenuBar = None):
        self.file_menu = menubar.addMenu('File')
        self._extensions_menu = menubar.addMenu('Extensions')
        self.action_menu = menubar.addMenu('Actions')

    def setup_docks(self):
        self.dock_command = Dock('Scan Command')
        self.dockarea.addDock(self.dock_command)

        widget_command = QtWidgets.QWidget()
        widget_command.setLayout(QtWidgets.QVBoxLayout())
        self.dock_command.addWidget(widget_command)
        widget_command.layout().addWidget(self._toolbar)

        splitter_widget = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter_v_widget = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        widget_command.layout().addWidget(splitter_widget)
        splitter_widget.addWidget(splitter_v_widget)
        self.module_widget = QtWidgets.QWidget()
        self.module_widget.setLayout(QtWidgets.QVBoxLayout())
        self.module_widget.setMinimumWidth(220)
        self.module_widget.setMaximumWidth(400)

        self.plotting_widget = QtWidgets.QWidget()
        self.plotting_widget.setLayout(QtWidgets.QVBoxLayout())
        self.plotting_widget.setMinimumWidth(220)
        self.plotting_widget.setMaximumWidth(400)

        settings_widget = QtWidgets.QWidget()
        settings_widget.setLayout(QtWidgets.QVBoxLayout())
        settings_widget.setMinimumWidth(220)

        splitter_v_widget.addWidget(self.module_widget)
        splitter_v_widget.addWidget(self.plotting_widget)

        splitter_v_widget.setSizes([400, 400])
        splitter_widget.addWidget(settings_widget)


        self._statusbar = QtWidgets.QStatusBar()
        self.mainwindow.setStatusBar(self._statusbar)
        self.populate_status_bar()

        self.settings_toolbox = QtWidgets.QToolBox()
        settings_widget.layout().addWidget(self.settings_toolbox)
        self.scanner_widget = QtWidgets.QWidget()
        self.scanner_widget.setLayout(QtWidgets.QVBoxLayout())
        self.settings_toolbox.addItem(self.scanner_widget, 'Scanner Settings')

    def add_settings_toolbox_widget(self, widget: QtWidgets.QWidget, name: str):
        """Add a widget, usaually a ParameterTree to the SettingsToolbox"""
        self.settings_toolbox.addItem(widget, name)

    def add_scanner_settings(self, tree: 'ParameterTree'):
        """Adds a  ParameterTree to the Scanner settings widget"""
        self.scanner_widget.layout().addWidget(tree)

    def populate_toolbox_widget(self, widgets: List[QtWidgets.QWidget], names: List[str]):
        for widget, name in zip(widgets, names):
            self.settings_toolbox.addItem(widget, name)

    def set_scanner_settings(self, settings_tree: QtWidgets.QWidget):
        while True:
            child = self.scanner_widget.layout().takeAt(0)
            if not child:
                break
            child.widget().deleteLater()
            QtWidgets.QApplication.processEvents()

        self.scanner_widget.layout().addWidget(settings_tree)

    def set_modules_settings(self, settings_widget):
        self.module_widget.layout().addWidget(settings_widget)

    def set_plotting_settings(self, settings_plotting):
        self.plotting_widget.layout().addWidget(settings_plotting)

    def populate_status_bar(self):
        self._status_message_label = QtWidgets.QLabel('Initializing')
        self._n_scan_steps_sb = QSpinBox_ro()
        self._n_scan_steps_sb.setToolTip('Total number of steps')
        self._indice_scan_sb = QSpinBox_ro()
        self._indice_scan_sb.setToolTip('Current step value')
        self._indice_average_sb = QSpinBox_ro()
        self._indice_average_sb.setToolTip('Current average value')
        
        self._scan_done_LED = QLED()
        self._scan_done_LED.set_as_false()
        self._scan_done_LED.clickable = False
        self._scan_done_LED.setToolTip('Scan done state')
        self._statusbar.addPermanentWidget(self._status_message_label)

        self._statusbar.addPermanentWidget(self._n_scan_steps_sb)
        self._statusbar.addPermanentWidget(self._indice_scan_sb)
        self._statusbar.addPermanentWidget(self._indice_average_sb)
        self._indice_average_sb.setVisible(False)
        self._statusbar.addPermanentWidget(self._scan_done_LED)

    @property
    def n_scan_steps(self):
        return self._n_scan_steps_sb.value()

    @n_scan_steps.setter
    def n_scan_steps(self, nsteps: int):
        self._n_scan_steps_sb.setValue(nsteps)

    def display_status(self, status: str, wait_time=1000):
        self._statusbar.showMessage(status, wait_time)
        
    def set_permanent_status(self, status: str):
        self._status_message_label.setText(status)

    def set_scan_step(self, step_ind: int):
        self._indice_scan_sb.setValue(step_ind)

    def show_average_step(self, show: bool = True):
        self._indice_average_sb.setVisible(show)

    def set_scan_step_average(self, step_ind: int):
        self._indice_average_sb.setValue(step_ind)

    def set_scan_done(self, done=True):
        self._scan_done_LED.set_as(done)

    def update_viewers(self, viewers_type: List[ViewersEnum], viewers_name: List[str] = None, force=False):
        super().update_viewers(viewers_type, viewers_name, force)
        self.command_sig.emit(ThreadCommand('viewers_changed', attribute=dict(viewer_types=self.viewer_types,
                                                                              viewers=self.viewers)))

def main():

    app = QtWidgets.QApplication(sys.argv)

    win = QtWidgets.QMainWindow()
    dockarea = DockArea()
    win.setCentralWidget(dockarea)
    win.resize(1000, 500)
    win.setWindowTitle('DAQScan Extension')

    prog = DAQScanUI(dockarea)
    win.show()


    def print_command_sig(cmd_sig):
        print(cmd_sig)
        prog.display_status(str(cmd_sig))

    prog.command_sig.connect(print_command_sig)
    prog.update_viewers([ViewersEnum['Viewer0D'], ViewersEnum['Viewer1D'], ViewersEnum['Viewer2D']])

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
