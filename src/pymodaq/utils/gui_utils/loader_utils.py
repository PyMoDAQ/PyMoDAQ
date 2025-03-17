from pathlib import Path

from qtpy import QtWidgets

from pymodaq.dashboard import DashBoard
from pymodaq.utils.gui_utils import DockArea
from pymodaq.utils.config import get_set_preset_path
from pymodaq.extensions.utils import CustomExt


def load_dashboard_with_preset(preset_name: str, extension_name: str) -> \
        (DashBoard, CustomExt, QtWidgets.QMainWindow):
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
    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('extension_name')
    win.show()

    # win.setVisible(False)
    dashboard = DashBoard(area)

    preset_name = Path(preset_name).stem

    file = Path(get_set_preset_path()).joinpath(f"{preset_name}.xml")

    if file is not None and file.exists():
        dashboard.set_preset_mode(file)
        if extension_name == 'DAQScan':
            extension = dashboard.load_scan_module()
        elif extension_name == 'DAQLogger':
            extension = dashboard.load_log_module()
        elif extension_name == 'DAQ_PID':
            extension = dashboard.load_pid_module()
        elif extension_name == 'Bayesian':
            extension = dashboard.load_bayesian()
        else:
            extension = dashboard.load_extension_from_name(extension_name)
    else:
        msgBox = QtWidgets.QMessageBox()
        msgBox.setText(f"The default file specified in the configuration file does not exists!\n"
                       f"{file}\n"
                       f"Impossible to load the {extension_name} extension")
        msgBox.setStandardButtons(msgBox.Ok)
        ret = msgBox.exec()
    return dashboard, extension, win