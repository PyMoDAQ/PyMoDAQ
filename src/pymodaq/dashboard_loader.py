from qtpy import QtGui, QtWidgets, QtCore

from pymodaq.dashboard import DashBoard

from pymodaq_gui.utils import DockArea
from pymodaq_gui.utils.utils import mkQApp

from pymodaq.utils.gui_utils.loader_utils import load_dashboard_with_preset

import argparse


def main():

    app = mkQApp('Dashboard')

    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Dashboard')

    # Command-line argument parsing
    parser = argparse.ArgumentParser(prog="dashboard", description="PyMoDAQ dashboard")
    parser.add_argument("-p", "--preset", metavar="PRESET_NAME", help="preset name to load")
    args = parser.parse_args()

    # If preset name is supplied, load dashboard with this preset
    if args.preset:
        load_dashboard_with_preset(args.preset)

    # If no command-line arguments are supplied, start empty
    else:
        prog = DashBoard(area)
        win.show()

    app.exec()


if __name__ == "__main__":
    main()
