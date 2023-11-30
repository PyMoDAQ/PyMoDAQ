from qtpy import QtWidgets, QtCore
from pyqtgraph.widgets.SpinBox import SpinBox
from pyqtgraph.parametertree.parameterTypes.basetypes import WidgetParameterItem
from pymodaq.utils.parameter.utils import scroll_log, scroll_linear
import numpy as np


class SliderSpinBox(QtWidgets.QWidget):

    def __init__(self, *args, subtype='lin', **kwargs):

        super().__init__()
        self.subtype = subtype
        self.initUI(*args, **kwargs)

        self.valueChanged = self.spinbox.valueChanged  # (value)  for compatibility with QSpinBox
        self.sigValueChanged = self.spinbox.sigValueChanged  # (self)
        self.sigValueChanging = self.spinbox.sigValueChanging  # (self, value)  sent immediately; no delay.
        self.sigChanged = self.spinbox.sigValueChanged

    @property
    def opts(self):
        return self.spinbox.opts

    @opts.setter
    def opts(self, **opts):
        self.setOpts(**opts)

    def setOpts(self, **opts):
        self.spinbox.setOpts(**opts)
        if 'visible' in opts:
            self.slider.setVisible(opts['visible'])

    def insert_widget(self ,widget, row=0):
        self.vlayout.insertWidget(row, widget)

    def initUI(self, *args, **kwargs):
        """
            Init the User Interface.
        """
        self.vlayout = QtWidgets.QVBoxLayout()
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setMinimumWidth(50)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        if 'value' in kwargs:
            value = kwargs.pop('value')
        else:
            if 'bounds' in kwargs:
                value = kwargs['bounds'][0]
            else:
                value = 1
        self.spinbox = SpinBox(parent=None, value=value, **kwargs)

        self.vlayout.addWidget(self.slider)
        self.vlayout.addWidget(self.spinbox)
        self.vlayout.setSpacing(0)
        self.vlayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.vlayout)

        self.slider.valueChanged.connect(self.update_spinbox)
        self.spinbox.valueChanged.connect(self.update_slide)

    def update_spinbox(self, val):
        """
        val is a percentage [0-100] used in order to set the spinbox value between its min and max
        """
        min_val = float(self.opts['bounds'][0])
        max_val = float(self.opts['bounds'][1])
        if self.subtype == 'log':
            val_out = scroll_log(val, min_val, max_val)
        else:
            val_out = scroll_linear(val, min_val, max_val)
        try:
            self.slider.valueChanged.disconnect(self.update_spinbox)
            self.spinbox.valueChanged.disconnect(self.update_slide)
        except Exception:
            pass
        self.spinbox.setValue(val_out)

        self.slider.valueChanged.connect(self.update_spinbox)
        self.spinbox.valueChanged.connect(self.update_slide)

    def update_slide(self, val):
        """
        val is the spinbox value between its min and max
        """
        min_val = float(self.opts['bounds'][0])
        max_val = float(self.opts['bounds'][1])

        try:
            self.slider.valueChanged.disconnect(self.update_spinbox)
            self.spinbox.valueChanged.disconnect(self.update_slide)
        except Exception:
            pass
        if self.subtype == 'linear':
            value = int((val - min_val) / (max_val - min_val) * 100)
        else:
            value = int((np.log10(val) - np.log10(min_val)) / (np.log10(max_val) - np.log10(min_val)) * 100)
        self.slider.setValue(value)
        self.slider.valueChanged.connect(self.update_spinbox)
        self.spinbox.valueChanged.connect(self.update_slide)

    def setValue(self, val):
        self.spinbox.setValue(val)

    def value(self):
        return self.spinbox.value()


class SliderParameterItem(WidgetParameterItem):
    """Registered parameter type which displays a QLineEdit"""

    def makeWidget(self):
        opts = self.param.opts
        defs = {
            'value': 0, 'min': None, 'max': None,
            'step': 1.0, 'dec': False,
            'siPrefix': False, 'suffix': '', 'decimals': 12,
            'int': False
        }
        if 'subtype' not in opts:
            opts['subtype'] = 'linear'
        defs['bounds'] = [0., self.param.value()]  # max value set to default value when no max given
        if 'limits' not in opts:
            if 'min' in opts:
                defs['bounds'][0] = opts['min']
            if 'max' in opts:
                defs['bounds'][1] = opts['max']
        else:
            defs['bounds'] = opts['limits']

        if 'int' in opts:
            defs['int'] = opts['int']

        w = SliderSpinBox(subtype=opts['subtype'], bounds=defs['bounds'], value=defs['value'], int=defs['int'])
        self.setSizeHint(1, QtCore.QSize(50, 50))
        return w