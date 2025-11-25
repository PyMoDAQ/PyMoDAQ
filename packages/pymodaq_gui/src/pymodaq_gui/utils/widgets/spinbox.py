from qtpy import QtWidgets, QtGui, QtCore
from pyqtgraph.widgets.SpinBox import SpinBox


class SpinBox(SpinBox):
    """
    In case I want to add pyqtgraph spinbox functionalities
    """
    def __init__(self, *args, font_size=None, min_height=20, **kwargs):
        super().__init__(*args, **kwargs)

        if font_size is not None:
            self.set_font_size(font_size)
        self.setMinimumHeight(min_height)

    def set_font_size(self, font_size):
        font = QtGui.QFont()
        font.setPointSize(font_size)
        self.setFont(font)


class QSpinBoxWithShortcut(SpinBox):
    """
    QSpinBox but which accepts key sequences and store them as attribute
    For now, it does not apply to regular input such as text or numerics.

    Beware I could not make it run for the KeySequence Ctrl+Enter or any combination involving enter...

    """
    def __init__(self, *args, key_sequences=("Ctrl+E",), **kwargs):

        super().__init__(*args, **kwargs)

        self.shortcut = dict() #Store shortcuts in a dictionnary
        for key_sequence in key_sequences:
            shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(key_sequence), self)
            shortcut.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
            self.shortcut[key_sequence] = shortcut


class QSpinBox_ro(SpinBox):
    def __init__(self, *args, readonly=True, **kwargs):
        super().__init__(*args, **kwargs)
        #self.setMaximum(100000)
        self.setReadOnly(readonly)
        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)


if __name__ == '__main__':

    from pymodaq_gui.utils.utils import mkQApp

    app = mkQApp('Test Spinbox')

    spinbox = QSpinBoxWithShortcut(key_sequences=('Ctrl+E', 'Ctrl+Shift+E', 'Ctrl+Enter', 'Ctrl+Shift+Enter'))
    def print_spinbox(value):
        print(value)
    spinbox.shortcut['Ctrl+E'].activated.connect(lambda: print_spinbox(f'Ctrl+E: {spinbox.value()}'))
    spinbox.shortcut['Ctrl+Shift+E'].activated.connect(lambda: print_spinbox(f'Ctrl+Shift+E: {spinbox.value()}'))
    spinbox.shortcut['Ctrl+Shift+Enter'].activated.connect(lambda: print_spinbox(f'Ctrl+Shift+Enter: {spinbox.value()}'))
    spinbox.shortcut['Ctrl+Enter'].activatedAmbiguously.connect(lambda: print_spinbox(f'Ctrl+Enter: {spinbox.value()}'))
    spinbox.show()

    app.exec()