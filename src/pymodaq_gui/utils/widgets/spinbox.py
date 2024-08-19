from qtpy import QtWidgets, QtGui
from pyqtgraph.widgets.SpinBox import SpinBox


class SpinBox(SpinBox):
    """
    In case I want to add pyqtgraph spinbox functionalities
    """
    def __init__(self, *args, font_size=None, min_height=20, **kwargs):
        super().__init__(*args, **kwargs)

        if font_size is not None:
            font = QtGui.QFont()
            font.setPointSize(font_size)
            self.setFont(font)
        self.setMinimumHeight(min_height)


class QSpinBox_ro(SpinBox):
    def __init__(self, *args, readonly=True, **kwargs):
        super().__init__(*args, **kwargs)
        #self.setMaximum(100000)
        self.setReadOnly(readonly)
        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
