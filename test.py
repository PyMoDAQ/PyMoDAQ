from PyQt5 import QtWidgets
import sys

from pymodaq.daq_utils.daq_utils import make_enum

DAQ_0DViewer_Det_type = make_enum('daq_0Dviewer')
DAQ_1DViewer_Det_type = make_enum('daq_1Dviewer')
DAQ_2DViewer_Det_type = make_enum('daq_2Dviewer')

from pymodaq.daq_utils.daq_utils import get_set_local_dir
local_path = get_set_local_dir()

from pymodaq.daq_utils.daq_utils import select_file

def do():
    save_file_pathname = select_file(None, save=True, ext='h5')  # see daq_utils
    print(save_file_pathname)


if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)
    do()
    sys.exit(app.exec_())