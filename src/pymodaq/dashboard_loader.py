from qtpy import QtGui, QtWidgets, QtCore

from pymodaq.dashboard import DashBoard

from pymodaq_gui.utils import DockArea
from pymodaq_gui.utils.utils import mkQApp


def main():

    # Create application and main window
    app = mkQApp('Dashboard')
    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Dashboard')

    # Create and show dashboard
    prog = DashBoard(area)
    win.show()

    # Run application
    app.exec()


if __name__ == "__main__":
    main()
