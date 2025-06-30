from qtpy import QtGui, QtWidgets, QtCore

from pymodaq.dashboard import DashBoard

from pymodaq_gui.utils import DockArea
from pymodaq_gui.utils.utils import mkQApp

from pymodaq.utils.gui_utils.loader_utils import load_dashboard_with_preset

import sys


def main():

    app = mkQApp('Dashboard')

    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Dashboard')

    # If supplied with a command-line argument, start with preset
    if len(sys.argv) > 1:
        preset_name = sys.argv[1]
        load_dashboard_with_preset(preset_name)

    # If no command-line arguments are supplied, start empty
    else:
        prog = DashBoard(area)
        win.show()

    app.exec()


if __name__ == "__main__":
    main()
