import argparse
from pathlib import Path
import sys

from qtpy import QtWidgets

from pymodaq.utils.h5modules.browsing import H5Browser
from pymodaq.utils.config import Config


config = Config()


def main(h5file_path: Path = None):
    app = QtWidgets.QApplication(sys.argv)
    if config['style']['darkstyle']:
        import qdarkstyle
        app.setStyleSheet(qdarkstyle.load_stylesheet())

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
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
