from qtpy import QtWidgets

from pyqtgraph.parametertree import parameterTypes, Parameter, ParameterTree
from . import pymodaq_ptypes

__parameter_value_old_fun = Parameter.value
def __parameter_value_monkey_path(self):
    try:
        return __parameter_value_old_fun(self)
    except ValueError:
        return None

Parameter.value = __parameter_value_monkey_path

class ParameterTree(ParameterTree):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.header().setVisible(True)
        self.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        #self.header().setMinimumSectionSize(150)
