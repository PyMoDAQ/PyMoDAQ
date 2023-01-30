# -*- coding: utf-8 -*-
"""
Created the 30/01/2023

@author: Sebastien Weber
"""

from qtpy import QtWidgets, QtCore, QtSvg, QtGui
from pymodaq.daq_utils.config import Config, get_set_preset_path
from pymodaq.daq_utils.managers.modules_manager import ModulesManager
from pathlib import Path
from pymodaq.examples.logger_image.setup_svg import SetupSVG
from pymodaq.daq_utils.gui_utils import CustomApp
from pymodaq.daq_utils.managers.action_manager import ActionManager
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_logger import DAQ_Logger

config = Config()
logger = utils.set_logger(utils.get_module_name(__file__))


class LoggerDisplayer(ActionManager):

    def __init__(self, main_window: QtWidgets.QMainWindow, logger: DAQ_Logger):
        super().__init__()

        self.main_window = main_window
        widget = QtWidgets.QWidget()
        self.main_window.setCentralWidget(widget)
        self.ui = SetupSVG(widget)

        self.logger = logger
        self.logger.set_logger('H5 File')
        self.logger.start_logging()
        self.modules_manager = logger.modules_manager
        self.modules_manager.selected_detectors_name = self.modules_manager.detectors_name
        self.modules_manager.selected_actuators_name = self.modules_manager.actuators_name

        self._toolbar = QtWidgets.QToolBar()

        if self.main_window is not None:
            self.main_window.addToolBar(self._toolbar)
            self.statusbar = self.main_window.statusBar()

        self.set_toolbar(self._toolbar)

        self.setup_actions()
        self.connect_things()

    def setup_actions(self):
        logger.debug('setting actions')
        self.add_action('quit', 'Quit', 'close2', "Quit program", toolbar=self.toolbar)
        self.add_action('run', 'Log', 'run2', "Log", checkable=True, toolbar=self.toolbar)
        self.add_action('load', 'Load', 'Open', "Open log File", toolbar=self.toolbar)
        self.add_action('show', 'Show/hide', 'read2', "Show Hide Main Modules", checkable=True, toolbar=self.toolbar)

        logger.debug('actions set')

    def connect_things(self):
        self.connect_action('run', self.run_detectors)
        self.connect_action('show', self.show_dashboard)
        self.connect_action('load', self.logger.logger.h5saver.show_file_content)

        self.modules_manager.connect_detectors(True, self.update_data)
        for act in self.modules_manager.actuators:
            act.move_moving_signal.connect(self.update_actuators)

    def show_dashboard(self):
        self.logger.dashboard.mainwindow.setVisible(self.is_action_checked('show'))
        self.logger.mainwindow.setVisible(self.is_action_checked('show'))

    def run_detectors(self):
        for det in self.modules_manager.detectors:
            det.grab()

    def update_data(self, data):
        for key in data['data0D']:
            if 'Rep. Rate' in key:
                self.ui.update('rep_rate', float(data['data0D'][key].data))
            elif 'Power' in key:
                self.ui.update('power', float(data['data0D'][key].data))

    def update_actuators(self, name, value):
        self.ui.update(name, value)


def main():
    import sys
    from pymodaq.dashboard import DashBoard
    from pathlib import Path
    from pymodaq.daq_utils.gui_utils.dock import DockArea

    app = QtWidgets.QApplication(sys.argv)
    # if config('style', 'darkstyle'):
    #     import qdarkstyle
    #     app.setStyleSheet(qdarkstyle.load_stylesheet())

    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Dashboard')

    prog = DashBoard(area)
    file = Path(get_set_preset_path()).joinpath(f"amplitude_demo.xml")
    if file.exists():
        prog.set_preset_mode(file)
        log_module = prog.load_log_module()
        displayer_window = QtWidgets.QMainWindow()
        displayer = LoggerDisplayer(displayer_window, log_module)
        displayer_window.show()
        log_module.mainwindow.setVisible(False)
        win.setVisible(False)

        log_module.modules_manager.connect_detectors(displayer.update_data)

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
