
from qtpy import QtWidgets


class StatuBarSeparator(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QtWidgets.QFrame.Shape.VLine)  # Sets shape to a vertical line
        self.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken) # Adds depth
