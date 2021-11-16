import sys
from qtpy import QtWidgets
from pymodaq.daq_utils.h5modules import H5Browser
from pymodaq import load_config

config = load_config()

def main():
    app = QtWidgets.QApplication(sys.argv)
    if config['style']['darkstyle']:
        import qdarkstyle
        app.setStyleSheet(qdarkstyle.load_stylesheet())

    win = QtWidgets.QMainWindow()
    prog = H5Browser(win)
    win.show()
    QtWidgets.QApplication.processEvents()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
