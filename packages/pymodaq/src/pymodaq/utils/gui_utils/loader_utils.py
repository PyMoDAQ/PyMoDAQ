from pathlib import Path
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMessageBox, QMainWindow

from pymodaq import dashboard
from pymodaq.dashboard import DashBoard
from pymodaq.utils.gui_utils import DockArea
from pymodaq.utils.config import get_set_preset_path
from pymodaq.extensions.utils import CustomExt

from pymodaq.utils.shared_ui import SharedUI
from pymodaq.utils.config import Config as ControlModulesConfig

config = ControlModulesConfig()


def load_dashboard_with_preset(preset_name: str, extension_name: str) -> \
        (DashBoard, CustomExt, QMainWindow):

    """ Load the Dashboard using a given preset then load an extension

    Parameters
    ----------
    preset_name: str
        The filename (without extension) defining the preset to be loaded in the Dashboard
    extension_name: str
        The name of the extension. Either the builtins ones:
        * 'DAQScan'
        * 'DAQLogger'
        * 'DAQ_PID'
        * 'Bayesian'

        or the ones defined within a plugin

    Returns
    -------

    """
    shared_ui, dashboard = create_load_dashboard()


    preset_name = Path(preset_name).stem
    extension = None

    if preset_name in dashboard.preset_manager.entries:
        dashboard.preset_manager.entry = preset_name

        if extension_name:
            if extension_name == 'DAQScan':
                extension = dashboard.load_scan_module()
            elif extension_name == 'DAQLogger':
                extension = dashboard.load_log_module()
            elif extension_name == 'DAQ_PID':
                extension = dashboard.load_pid_module()
            elif extension_name == 'Bayesian':
                extension = dashboard.load_bayesian()
            elif extension_name == 'AdaptiveScan':
                extension = dashboard.load_adaptive()
            elif extension_name == 'Data Mixer':
                extension = dashboard.load_datamixer()
            else:
                extension = dashboard.load_extension_from_name(extension_name)
        else:
            extension = None

    else:
        msgBox = QMessageBox()
        msgBox.setText(f"The default file specified in the configuration file does not exists!\n"
                       f"{preset_name}\n"
                       f"Impossible to load the {extension_name} extension")
        msgBox.setStandardButtons(QMessageBox.StandardButton.Ok)
        ret = msgBox.exec()
    return dashboard, extension, shared_ui


def create_load_dashboard():

    win = QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle("PyMoDAQ Dashboard")

    shared_ui = SharedUI(win)
    dashboard = DashBoard(area)
    shared_ui.affect_application(dashboard)
    return shared_ui, dashboard

def create_load_daq_move():
    from pymodaq.control_modules.daq_move import DAQ_Move

    widget = QtWidgets.QWidget()
    daq_move = DAQ_Move(widget, title="test")

    shared_ui = SharedUI(widget)
    shared_ui.affect_application(daq_move)

    if config("actuator", "ui") == "Original":
        shared_ui.add_toolbar('ui_toolbar', 'ui_toolbar', toolbar=daq_move.ui.toolbar,
                              area=Qt.ToolBarArea.LeftToolBarArea)
        shared_ui.add_toolbar('move_toolbar', 'move_toolbar', toolbar=daq_move.ui.move_toolbar,
                              area=Qt.ToolBarArea.TopToolBarArea,
                              add_break=True)
    else:
        shared_ui.add_toolbar('move_toolbar', 'move_toolbar', toolbar=daq_move.ui.move_toolbar,
                              area=Qt.ToolBarArea.TopToolBarArea,
                              add_break=True)

    return shared_ui, daq_move


def create_load_daq_viewer():
    from pymodaq.control_modules.daq_viewer import DAQ_Viewer

    widget = QtWidgets.QWidget()
    daq_viewer = DAQ_Viewer(widget, title="test")

    shared_ui = SharedUI(widget)
    shared_ui.affect_application(daq_viewer)
    shared_ui.add_toolbar('viewer', 'Viewer', toolbar=daq_viewer.ui.toolbar, add_break=True)

    return shared_ui, daq_viewer