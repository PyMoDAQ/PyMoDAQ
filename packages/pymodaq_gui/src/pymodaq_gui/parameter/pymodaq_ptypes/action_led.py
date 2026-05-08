import warnings
from qtpy import QtWidgets, QtCore
from pyqtgraph.parametertree.parameterTypes.basetypes import WidgetParameterItem, SimpleParameter

from pymodaq_gui.utils.widgets import MultistateLED, DEFAULT_STATES


class ActionLedWidget(QtWidgets.QWidget):
    """A push button alongside a non-clickable LED status indicator.

    The button fires the action; the LED reflects the current state.
    """

    def __init__(self, label='▶', states=None):
        super().__init__()
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.button = QtWidgets.QPushButton(label)
        self.led = MultistateLED(states=states if states is not None else DEFAULT_STATES, readonly=True)

        layout.addWidget(self.button, stretch=1)
        layout.addWidget(self.led, stretch=0)

        # WidgetParameterItem interface: value tracks LED state (str)
        self.sigChanged = self.led.state_changed
        self.value = self.led.get_state
        self.setValue = self._set_value

    def _set_value(self, v):
        if isinstance(v, bool):
            warnings.warn(
                "ActionLedWidget.setValue() received a bool; pass a state name string "
                "('true'/'false') instead. Bool support will be removed in a future version.",
                DeprecationWarning,
                stacklevel=2,
            )
            v = 'true' if v else 'false'
        self.led.set_state(v)


class ActionLedParameterItem(WidgetParameterItem):
    def makeWidget(self):
        opts = self.param.opts
        w = ActionLedWidget(
            label=opts.get('label', '▶'),
            states=opts.get('states', None),
        )
        w.button.clicked.connect(self.param.activate)
        self.hideWidget = False
        return w

    def updateDefaultBtn(self):
        self.defaultBtn.setVisible(False)


class ActionLedParameter(SimpleParameter):
    """Parameter type combining a trigger button and a LED status indicator.

    - Clicking the button emits ``sigActivated`` (same as the ``action`` type).
    - ``param.setValue(str)`` / ``param.value()`` controls the LED state by name.

    Options
    -------
    label : str, optional
        Text shown on the push button. Defaults to ``'▶'``.
    states : list of (str, str | QColor), optional
        Forwarded to :class:`~pymodaq_gui.utils.widgets.MultistateLED`.
        Defaults to the two-state red/green set.
    """

    itemClass = ActionLedParameterItem
    sigActivated = QtCore.Signal(object)

    def _interpretValue(self, v):
        if isinstance(v, bool):
            warnings.warn(
                "ActionLedParameter value should be a state name string ('true'/'false'), "
                "not a bool. Bool support will be removed in a future version.",
                DeprecationWarning,
                stacklevel=2,
            )
            return 'true' if v else 'false'
        return str(v)

    def activate(self):
        self.sigActivated.emit(self)
        self.emitStateChanged('activated', None)
