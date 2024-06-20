from pathlib import Path

from qtpy import QtWidgets

from pymodaq.dashboard import DashBoard
from pymodaq.utils.gui_utils import DockArea
from pymodaq.utils.config import get_set_preset_path


def load_dashboard_with_preset(preset_name: str, extension_name: str):
    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Dashboard')
    win.show()

    # win.setVisible(False)
    dashboard = DashBoard(area)

    file = Path(get_set_preset_path()).joinpath(f"{preset_name}.xml")

    if file is not None and file.exists():
        dashboard.set_preset_mode(file)
        if extension_name == 'DAQScan':
            extension = dashboard.load_scan_module()
        elif extension_name == 'DAQLogger':
            extension = dashboard.load_log_module()
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