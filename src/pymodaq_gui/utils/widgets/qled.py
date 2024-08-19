import os
import numpy as np
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtWidgets import QLabel
from qtpy.QtCore import QObject, Signal
from pymodaq_gui.utils.utils import clickable


class QLED(QLabel):
    value_changed = Signal(bool)

    def __init__(self, parent=None, scale=1, readonly=True):
        QLabel.__init__(self, parent)
        # self.setText("")
        self.red_icon = QtGui.QPixmap(":/icons/Icon_Library/red_light.png")
        self.green_icon = QtGui.QPixmap(":/icons/Icon_Library/greenLight2.png")
        self.setPixmap(self.red_icon)
        self.state = False
        self.clickable = not readonly
        # set the possibility to click and control the state of the LED otherwise it behaves as an indicator
        clickable(self).connect(
            self.LED_Clicked)
        # clickable is a function importing a filter class to deal with mouse down event as a signal see GUI_utils
        self.setText("empty")
        self.setMaximumWidth(self.height())
        if scale != 1:
            self.scale(scale)
        self.set_as_false()

    def scale(self, scale):
        self.green_icon = self.green_icon.scaled(scale * self.green_icon.width(),
                                                 scale * self.green_icon.height())
        self.red_icon = self.red_icon.scaled(scale * self.red_icon.width(),
                                             scale * self.red_icon.height())

    def get_state(self):
        return self.state

    def set_as(self, state=True):

        if state:
            self.set_as_true()
        else:
            self.set_as_false()
        if state != self.state:
            self.value_changed.emit(state)

    def set_as_true(self):
        self.state = True
        self.setPixmap(self.green_icon)

    def set_as_false(self):
        self.state = False
        self.setPixmap(self.red_icon)

    def LED_Clicked(self):
        if self.clickable:
            if self.state:
                self.set_as_false()
            else:
                self.set_as_true()
            self.value_changed.emit(not self.state)
