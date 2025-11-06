from pathlib import Path

from qtpy import QtWidgets, QtGui, QtCore
from qtpy.QtCore import Qt


class MySplash(QtWidgets.QSplashScreen):

    def __init__(self, *args, **kwargs):
        here = Path(__file__)
        pixmap = QtGui.QPixmap(str(here.parent.parent.joinpath('splash.png')))
        super().__init__(pixmap, Qt.WindowStaysOnTopHint, *args, **kwargs)
        font = self.font()
        font.setPixelSize(18)
        self.setFont(font)

    def showMessage(self, message, *args, **kwargs):
        """ force any message to be printed in white in the right/top corner """
        super().showMessage(message, QtCore.Qt.AlignmentFlag.AlignRight, QtCore.Qt.GlobalColor.white,
                            )

def get_splash_sc() -> MySplash:
    return MySplash()
