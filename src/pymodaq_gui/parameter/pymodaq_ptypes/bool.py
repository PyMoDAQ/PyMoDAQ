from qtpy import QtWidgets
from pyqtgraph.parametertree.parameterTypes.basetypes import WidgetParameterItem, SimpleParameter


class BoolPushParameterItem(WidgetParameterItem):
    """Registered parameter type which displays a QLineEdit"""

    def makeWidget(self):
        opts = self.param.opts
        w = QtWidgets.QPushButton()
        if 'label' in opts:
            w.setText(opts['label'])
        elif 'title' in opts:
            w.setText(opts['title'])
        else:
            w.setText(opts['name'])
        # w.setMaximumWidth(50)
        w.setCheckable(True)
        w.sigChanged = w.toggled
        w.value = w.isChecked
        w.setValue = w.setChecked
        w.setEnabled(not opts.get('readonly', False))
        self.hideWidget = False
        return w


class BoolPushParameter(SimpleParameter):
    itemClass = BoolPushParameterItem

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
