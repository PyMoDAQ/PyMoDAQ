from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import Qt,QObject, pyqtSlot, QThread, pyqtSignal, QLocale, QRectF
import sys
from pymodaq.daq_viewer.daq_gui_settings import Ui_Form

from pymodaq.daq_utils.plotting.viewer0D.viewer0D_main import Viewer0D
from pymodaq.daq_utils.plotting.viewer1D.viewer1D_main import Viewer1D
from pymodaq.daq_utils.plotting.viewer2D.viewer2D_main import Viewer2D
from pymodaq.daq_utils.plotting.viewerND.viewerND_main import ViewerND
from pymodaq.daq_utils.scanner import Scanner
from pymodaq.daq_utils.plotting.navigator import Navigator
from pymodaq.daq_utils.tcp_server_client import TCPClient
from pymodaq.daq_utils.plotting.lcd import LCD
import pymodaq.daq_utils.daq_utils as daq_utils
from pymodaq.daq_utils.h5browser import browse_data
from pymodaq.daq_utils.daq_utils import ThreadCommand, make_enum, getLineInfo

from pymodaq_plugins.daq_viewer_plugins import plugins_0D
from pymodaq_plugins.daq_viewer_plugins import plugins_1D
from pymodaq_plugins.daq_viewer_plugins import plugins_2D

DAQ_0DViewer_Det_type = make_enum('daq_0Dviewer')
DAQ_1DViewer_Det_type = make_enum('daq_1Dviewer')
DAQ_2DViewer_Det_type = make_enum('daq_2Dviewer')


from collections import OrderedDict
import numpy as np

from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import pymodaq.daq_utils.custom_parameter_tree as custom_tree
import os
from easydict import EasyDict as edict

from pymodaq.daq_utils.daq_utils import DockArea
from pyqtgraph.dockarea import Dock
import pickle
import time
import datetime
import tables
from pathlib import Path
from pymodaq.daq_utils.h5saver import H5Saver
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