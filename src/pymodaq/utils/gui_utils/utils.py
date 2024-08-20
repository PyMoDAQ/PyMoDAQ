import sys

from qtpy.QtCore import QObject, Signal, QEvent, QBuffer, QIODevice, Qt
from qtpy import QtWidgets, QtCore, QtGui

from pathlib import Path
from pymodaq_utils.config import Config
from pymodaq_utils.logger import set_logger, get_module_name

config = Config()
logger = set_logger(get_module_name(__file__))


def get_splash_sc():
    here = Path(__file__)
    splash_sc = QtWidgets.QSplashScreen(
        QtGui.QPixmap(str(here.parent.parent.parent.joinpath('splash.png'))),
        Qt.WindowStaysOnTopHint)
    return splash_sc


