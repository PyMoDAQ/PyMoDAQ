# -*- coding: utf-8 -*-
"""
Created the 06/12/2022

@author: Sebastien Weber
"""
import sys

from qtpy import QtWidgets, QtCore

from pymodaq.utils.gui_utils import CustomApp
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.config import Config, get_set_preset_path
from pymodaq.utils.gui_utils import DockArea, Dock


config = Config()
logger = set_logger(get_module_name(__file__))


class DAQScanUI(CustomApp):
    def __init__(self, parent):
        super().__init__(parent)

        self.setup_docks()
        self.setup_actions()

    def setup_actions(self):
        self.add_action('quit', 'Quit the module', 'close2')
        self.add_action('set_scan', 'Set Scan', '')
        self.add_action('ini_positions', 'Init Positions', '')
        self.add_action('grab', 'Grab', 'run2', "Start the scan")
        self.add_action('stop', 'Stop', 'stop', "Stop the scan")

    def setup_docks(self):
        dock_command = Dock('Scan Command')
        self.dockarea.addDock(dock_command)

        widget_command = QtWidgets.QWidget()
        widget_command.setLayout(QtWidgets.QVBoxLayout())
        dock_command.addWidget(widget_command)

        widget_command.layout().addWidget(self._toolbar)

        settings_widget = QtWidgets.QWidget()
        widget_command.layout().addWidget(settings_widget)

        splitter = QtWidgets.QSplitter()

    def setup_menu(self):
        ...

    def connect_things(self):
        ...


def main():

    app = QtWidgets.QApplication(sys.argv)

    win = QtWidgets.QMainWindow()
    dockarea = DockArea()
    win.setCentralWidget(dockarea)
    win.resize(1000, 500)
    win.setWindowTitle('DAQScan Extension')

    prog = DAQScanUI(dockarea)
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
