from qtpy import QtWidgets, QtCore
from pyqtgraph.parametertree.parameterTypes.basetypes import WidgetParameterItem, SimpleParameter

from pymodaq_gui.utils.widgets import QLED


class ActionLedWidget(QtWidgets.QWidget):
    """A push button alongside a non-clickable LED status indicator.

    The button fires the action; the LED reflects the done/idle state.
    """

    def __init__(self, label='▶'):
        super().__init__()
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.button = QtWidgets.QPushButton(label)
        self.led = QLED()
        self.led.clickable = False
        self.led.set_as_false()

        layout.addWidget(self.button, stretch=1)
        layout.addWidget(self.led, stretch=0)

        # WidgetParameterItem interface: value tracks LED state
        self.sigChanged = self.led.value_changed
        self.value = self.led.get_state
        self.setValue = self.led.set_as


class ActionLedParameterItem(WidgetParameterItem):
    def makeWidget(self):
        opts = self.param.opts
        w = ActionLedWidget(label=opts.get('label', '▶'))
        w.button.clicked.connect(self.param.activate)
        self.hideWidget = False
        return w

    def updateDefaultBtn(self):
        """The LED state is transient status, not a user-editable value — hide the revert arrow."""
        self.defaultBtn.setVisible(False)


class ActionLedParameter(SimpleParameter):
    """Parameter type combining a trigger button and a LED status indicator.

    - Clicking the button emits ``sigActivated`` (same as the ``action`` type).
    - ``param.setValue(bool)`` / ``param.value()`` controls the LED colour.

    Options
    -------
    label : str, optional
        Text shown on the push button. Defaults to ``'▶'``.
    """

    itemClass = ActionLedParameterItem
    sigActivated = QtCore.Signal(object)

    def _interpretValue(self, v):
        return bool(v)

    def activate(self):
        self.sigActivated.emit(self)
        self.emitStateChanged('activated', None)
