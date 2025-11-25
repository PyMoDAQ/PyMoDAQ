import pytest


from pymodaq_gui.utils.widgets import QSpinBoxWithShortcut


def test_spinbox_shortcut(qtbot):
    spinbox = QSpinBoxWithShortcut()
    def print_spinbox(value):
        print(value)
    spinbox.shortcut['Ctrl+E'].activated.connect(lambda: print_spinbox(spinbox.value()))
    spinbox.show()

