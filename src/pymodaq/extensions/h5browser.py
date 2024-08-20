import argparse
from pathlib import Path
import sys
import os
from qtpy import QtWidgets
os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"
from pymodaq_gui.h5modules.browsing import H5Browser
from pymodaq.utils.config import Config


config = Config()


def main(h5file_path: Path = None):
    from pymodaq_gui.utils.utils import mkQApp
    import sys
    app = mkQApp('H5Browser')

    h5file_path_tmp = None
    parser = argparse.ArgumentParser(description="Opens HDF5 files and navigate their contents")
    parser.add_argument("-i", "--input", help="specify path to the file to be opened")
    args = parser.parse_args()

    if args.input:
        h5file_path_tmp = Path(args.input).resolve()  # Transform to absolute Path in case it is relative

        if not h5file_path_tmp.exists():
            print(f'Error: {args.input} does not exist. Opening h5browser without input file.')
            h5file_path_tmp = h5file_path

    win = QtWidgets.QMainWindow()
    prog = H5Browser(win, h5file_path=h5file_path_tmp)
    win.show()
    QtWidgets.QApplication.processEvents()

    app.exec()


if __name__ == '__main__':
    main()
