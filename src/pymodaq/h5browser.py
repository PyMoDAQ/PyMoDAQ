import sys
from qtpy import QtWidgets
from pymodaq.daq_utils.h5modules import H5Browser
from pymodaq.daq_utils.config import Config
import getopt, sys
from pathlib import Path

config = Config()

def main():
    app = QtWidgets.QApplication(sys.argv)
    if config['style']['darkstyle']:
        import qdarkstyle
        app.setStyleSheet(qdarkstyle.load_stylesheet())

    h5file_path = None
    try:
        opts, args = getopt.getopt(sys.argv[1:], "i:", ["input-file="])
    except getopt.GetoptError as err:
        print(err)
        sys.exit(2)

    for o, a in opts:
        if o in ("-i", "--input-file"):
            h5file_path = Path(a).resolve()  # Transform to absolute Path in case it is relative

    win = QtWidgets.QMainWindow()
    prog = H5Browser(win, h5file_path=h5file_path)
    win.show()
    QtWidgets.QApplication.processEvents()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
