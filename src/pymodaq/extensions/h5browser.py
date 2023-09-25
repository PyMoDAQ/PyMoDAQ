import sys
from qtpy import QtWidgets
from pymodaq.utils.h5modules.browsing import H5Browser
from pymodaq.utils.config import Config
from pathlib import Path

config = Config()


def main_without_qt(h5file_path: Path = None):
    win = QtWidgets.QMainWindow()
    prog = H5Browser(win, h5file_path=h5file_path)
    win.show()


def main(h5file_path: Path = None):
    app = QtWidgets.QApplication(sys.argv)
    if config['style']['darkstyle']:
        import qdarkstyle
        app.setStyleSheet(qdarkstyle.load_stylesheet())

    win = QtWidgets.QMainWindow()
    prog = H5Browser(win, h5file_path=h5file_path)
    win.show()
    QtWidgets.QApplication.processEvents()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
