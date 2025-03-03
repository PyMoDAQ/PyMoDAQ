from qtpy import QtWidgets, QtGui,QtCore
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

class QSpinBoxWithShortcut(SpinBox):
    """
    QSpinBox but which accepts key sequences and store them as attribute
    For now, it does not apply to regular input such as text or numerics.
    """
    def __init__(self, *args, key_sequences=("Ctrl+Enter",), **kwargs):
        super().__init__(*args, **kwargs)
        
        self.shortcut = dict() #Store shortcuts in a dictionnary
        for key_sequence in key_sequences:
            shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(key_sequence), self)
            shortcut.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
            self.shortcut[key_sequence] = shortcut
        
class QSpinBox_ro(SpinBox):
    def __init__(self, *args, readonly=True, **kwargs):
        super().__init__(*args, **kwargs)
        #self.setMaximum(100000)
        self.setReadOnly(readonly)
        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
