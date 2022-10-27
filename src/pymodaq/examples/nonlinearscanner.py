
import numpy as np

from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.gui_utils.custom_app import CustomApp
from pymodaq.utils.gui_utils.dock import DockArea, Dock
from pymodaq.utils.config import Config, get_set_preset_path
from qtpy import QtWidgets
from qtpy.QtCore import Signal, QLocale

from pymodaq.utils import gui_utils as gutils
from pymodaq.utils import daq_utils as utils


config = Config()
logger = set_logger(get_module_name(__file__))


class NonLinearScanner(CustomApp):

    positions_signal = Signal(np.ndarray)

    # list of dicts enabling the settings tree on the user interface
    params = [
        {'title': 'Init Position:', 'name': 'ini_pos', 'type': 'float', 'value': 0, },
        {'title': 'Saturation pos:', 'name': 'satu_pos', 'type': 'float', 'value': 5, },
        {'title': 'Start scan:', 'name': 'start_scan', 'type': 'float', 'value': 4, },
        {'title': 'Stop Scan:', 'name': 'stop_scan', 'type': 'float', 'value': 3, },
        {'title': 'Step Scan:', 'name': 'step_scan', 'type': 'float', 'value': -0.05, },
        {'title': 'Apply', 'name': 'apply', 'type': 'action',},

    ]

    def __init__(self, dockarea):
        
        super().__init__(dockarea)
        self.setup_ui()

    def setup_actions(self):
        '''
        subclass method from ActionManager
        '''
        logger.debug('setting actions')

        logger.debug('actions set')

    def setup_docks(self):
        '''
        subclass method from CustomApp
        '''
        logger.debug('setting docks')
        self.dock_settings = Dock('Settings', size=(350, 350))
        self.dockarea.addDock(self.dock_settings, 'left')
        self.dock_settings.addWidget(self.settings_tree, 10)
        logger.debug('docks are set')

    def connect_things(self):
        '''
        subclass method from CustomApp
        '''
        logger.debug('connecting things')
        self.settings.child('apply').sigActivated.connect(self.emit_positions)
        logger.debug('connecting done')

    def setup_menu(self):
        '''
        subclass method from CustomApp
        '''
        logger.debug('settings menu')


        logger.debug('menu set')

    def value_changed(self, param):
        logger.debug(f'calling value_changed with param {param.name()}')

        logger.debug(f'Value change applied')

    def update_positions(self):
        xini = self.settings.child('ini_pos').value()
        sat = self.settings.child('satu_pos').value()
        start = self.settings.child('start_scan').value()
        stop = self.settings.child('stop_scan').value()
        step = self.settings.child('step_scan').value()

        return np.concatenate((np.array([xini, sat]), utils.linspace_step(start, stop, step), np.array([xini])))

    def emit_positions(self):
        self.positions_signal.emit(np.transpose(np.array([self.update_positions()])))


def main():
    import sys
    from pathlib import Path
    app = QtWidgets.QApplication(sys.argv)

    from pymodaq.dashboard import DashBoard

    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Dashboard')

    dash = DashBoard(area)
    file = Path(get_set_preset_path()).joinpath(f"{config('presets', 'default_preset_for_scan')}.xml")
    if file.exists():
        dash.set_preset_mode(file)
        dash.load_scan_module()


    mainwindow = QtWidgets.QMainWindow()
    dockarea = DockArea()
    mainwindow.setCentralWidget(dockarea)

    prog = NonLinearScanner(dockarea)

    QtWidgets.QApplication.processEvents()
    prog.positions_signal.connect(dash.scan_module.scanner.update_tabular_positions)

    mainwindow.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
