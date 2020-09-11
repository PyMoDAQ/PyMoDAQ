import sys
from PyQt5 import QtWidgets
from pymodaq.daq_utils.h5modules import H5Browser

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = QtWidgets.QMainWindow()
    prog = H5Browser(win)
    win.show()
    QtWidgets.QApplication.processEvents()
    sys.exit(app.exec_())
