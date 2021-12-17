from qtpy import QtWidgets


class QSpinBox_ro(QtWidgets.QSpinBox):
    def __init__(self, **kwargs):
        super().__init__()
        self.setMaximum(100000)
        self.setReadOnly(True)
        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
