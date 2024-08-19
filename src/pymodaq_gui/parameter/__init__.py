from qtpy import QtWidgets

from pyqtgraph.parametertree import parameterTypes, Parameter, ParameterTree
from . import pymodaq_ptypes


class ParameterTree(ParameterTree):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.header().setVisible(True)
        self.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Interactive)
        self.header().setMinimumSectionSize(150)
