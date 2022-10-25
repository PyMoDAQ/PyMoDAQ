import sys
from qtpy import QtWidgets
from pymodaq.daq_utils.h5modules import H5Browser
from pymodaq.daq_utils.config import Config
from pathlib import Path

import argparse
parser = argparse.ArgumentParser(description="Opens HDF5 files and navigate their contents")
parser.add_argument("-i", "--input", help="specify path to the file to be opened")
args = parser.parse_args()

config = Config()


def main():
    app = QtWidgets.QApplication(sys.argv)
    if config['style']['darkstyle']:
        import qdarkstyle
        app.setStyleSheet(qdarkstyle.load_stylesheet())

    h5file_path = None

    if args.input:
        h5file_path = Path(args.input).resolve()  # Transform to absolute Path in case it is relative

        if not h5file_path.exists():
            print('Error: '+args.input+ ' does not exist. Opening h5browser without input file.')
            h5file_path = None

    win = QtWidgets.QMainWindow()
    prog = H5Browser(win, h5file_path=h5file_path)
    win.show()
    QtWidgets.QApplication.processEvents()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

