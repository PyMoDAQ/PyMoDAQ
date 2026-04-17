import argparse
from pathlib import Path
import sys
import os
from qtpy import QtWidgets

from pymodaq_gui.utils.shared_ui import SharedUI
from pymodaq_gui.utils.widgets.window import make_window

os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"
from pymodaq_gui.h5modules.browsing import H5Browser
from pymodaq_utils.config import GlobalConfig as Config


config = Config()


def main(h5file_path: Path = None):
    from pymodaq_gui.qt_utils import mkQApp
    import sys
    app = mkQApp('H5Browser')

    win, area = make_window(area=False, title='H5Browser')

    h5file_path_tmp = None
    parser = argparse.ArgumentParser(description="Opens HDF5 files and navigate their contents")
    parser.add_argument("-i", "--input", help="specify path to the file to be opened")
    args = parser.parse_args()

    if args.input:
        h5file_path_tmp = Path(args.input).resolve()  # Transform to absolute Path in case it is relative

        if not h5file_path_tmp.exists():
            print(f'Error: {args.input} does not exist. Opening h5browser without input file.')
            h5file_path_tmp = h5file_path

    h5browser = H5Browser(win, h5file_path=h5file_path_tmp)

    shared_ui = SharedUI(win)
    shared_ui.affect_application(h5browser)

    shared_ui.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
