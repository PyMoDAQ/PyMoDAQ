# -*- coding: utf-8 -*-
"""
Created the 30/01/2023

@author: Sebastien Weber
"""

from qtpy import QtWidgets, QtCore, QtSvg, QtGui
from pymodaq.daq_utils.config import Config
from pyqtgraph.widgets.SpinBox import SpinBox

config = Config()


class SpinBox(SpinBox):
    """
    In case I want to add pyqtgraph spinbox functionalities
    """
    def __init__(self, *args, font_size=None, min_height=20, readonly=True, **kwargs):
        super().__init__(*args, **kwargs)

        if font_size is not None:
            font = QtGui.QFont()
            font.setPointSize(font_size)
            self.setFont(font)
        self.setMinimumHeight(min_height)
        self.setReadOnly(readonly)
        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)


class LabelSpinBox(QtWidgets.QWidget):
    value_changed = QtCore.Signal(float)

    def __init__(self, parent: QtWidgets.QWidget, label: str, readonly: bool):
        super().__init__(parent)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.label = QtWidgets.QLabel(f'{label}:')
        self.spinbox = SpinBox(self, font_size=20, readonly=True)
        self.spinbox.setDecimals(3)
        self.layout().addWidget(self.label)
        self.layout().addWidget(self.spinbox)

        self.setMinimumHeight(70)

    @property
    def value(self) -> float:
        self.spinbox.value()

    @value.setter
    def value(self, value: float):
        self.spinbox.setValue(value)


class SetupSVG:

    def __init__(self, parent_widget: QtWidgets.QWidget):
        super().__init__()
        self.parent = parent_widget

        self.svg_widget = QtSvg.QSvgWidget('setup.svg')
        self.settings_widget = QtWidgets.QWidget()
        self.settings_widget.setLayout(QtWidgets.QVBoxLayout())

        self.tangerine_power = LabelSpinBox(self.svg_widget, 'Power', True)
        self.tangerine_rep_rate = LabelSpinBox(self.svg_widget, 'Rep. Rate', True)

        self.compressor_delay = LabelSpinBox(self.svg_widget, 'Delay Comp.', True)
        self.nopa_angle = LabelSpinBox(self.svg_widget, 'Angle', True)
        self.nopa_delay = LabelSpinBox(self.svg_widget, 'Delay NOPA', True)

        self._all = dict(power=self.tangerine_power, rep_rate=self.tangerine_rep_rate,
                         nopa_angle=self.nopa_angle, nopa_delay=self.nopa_delay)

        self.setup_ui()

    def add_settings(self, tree):
        self.settings_widget.layout().addWidget(tree)

    def setup_ui(self):
        self.parent.setLayout(QtWidgets.QHBoxLayout())

        self.svg_widget.setFixedSize(1000, 700)
        self.parent.layout().addWidget(self.settings_widget)
        self.parent.layout().addWidget(self.svg_widget)
        self.svg_widget.renderer().setAspectRatioMode(QtCore.Qt.KeepAspectRatio)
        self.parent.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))

        self.tangerine_power.move(350, 20)
        self.tangerine_rep_rate.move(350, 100)
        self.compressor_delay.move(700, 200)
        self.nopa_angle.move(400, 220)
        self.nopa_delay.move(150, 630)

    def update(self, id: str, value: float):
        if id in self._all:
            self._all[id].value = value


def main(init_qt=True):
    import sys
    if init_qt: # used for the test suite
        app = QtWidgets.QApplication(sys.argv)

    widget = QtWidgets.QWidget()
    prog = SetupSVG(widget)
    widget.show()

    if init_qt:
        sys.exit(app.exec_())
    return prog, widget


if __name__ == '__main__':
    main()
