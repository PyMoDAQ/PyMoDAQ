import sys
from PyQt5 import QtWidgets
from pymodaq.daq_utils.h5modules import H5Browser


def main():
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    prog = H5Browser(win)
    win.show()
    QtWidgets.QApplication.processEvents()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
