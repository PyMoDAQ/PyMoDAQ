import warnings
from enum import Enum
from qtpy import QtWidgets, QtCore
from pyqtgraph.parametertree.parameterTypes.basetypes import WidgetParameterItem, SimpleParameter

from pymodaq_gui.utils.widgets import MultistateLED, DEFAULT_STATES, LedState
from pymodaq_gui.utils.status_palette import StatusPalette


def resolve_states(states):
    """Turn the ``states`` option of an ``action_led`` parameter into ``(name, color)`` pairs

    ``None`` gives the default two states, ``'status'`` all the states of the
    :class:`~pymodaq_gui.utils.status_palette.Status` workflow, a list of names (``Status`` members or the
    equivalent strings) the corresponding subset of it, coloured with the
    :class:`~pymodaq_gui.utils.status_palette.StatusPalette`; ``(name, color)`` pairs are used as they are.
    """
    if states is None:
        return DEFAULT_STATES
    if isinstance(states, str):
        if states != 'status':
            raise ValueError(f"Unknown states {states!r}: use 'status', a list of names or (name, color) pairs")
        return StatusPalette.as_states()
    states = list(states)
    if states and all(isinstance(state, str) for state in states):
        return StatusPalette.subset(*states)
    return states


class ActionLedWidget(QtWidgets.QWidget):
    """A push button alongside a non-clickable LED status indicator.

    The button fires the action; the LED reflects the current state. With ``checkable`` the button stays pressed
    until it is pressed again.
    """

    def __init__(self, label='▶', states=None, checkable=False):
        super().__init__()
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.button = QtWidgets.QPushButton(label)
        self.button.setCheckable(checkable)
        self.led = MultistateLED(states=resolve_states(states), readonly=True)

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
            v = LedState.TRUE if v else LedState.FALSE
        self.led.set_state(v)


class ActionLedParameterItem(WidgetParameterItem):
    def makeWidget(self):
        opts = self.param.opts
        w = ActionLedWidget(
            label=opts.get('label', '▶'),
            states=opts.get('states', None),
            checkable=opts.get('checkable', False),
        )
        if opts.get('checkable', False):
            w.button.setChecked(bool(opts.get('checked', False)))
            w.button.toggled.connect(self.param.toggle)
        else:
            w.button.clicked.connect(self.param.activate)
        self.hideWidget = False
        return w

    def optsChanged(self, param, opts):
        super().optsChanged(param, opts)
        if 'checked' in opts and self.widget is not None and self.widget.button.isCheckable():
            self.widget.button.blockSignals(True)  # the change comes from the parameter: do not activate it again
            self.widget.button.setChecked(bool(opts['checked']))
            self.widget.button.blockSignals(False)

    def updateDefaultBtn(self):
        self.defaultBtn.setVisible(False)


class ActionLedParameter(SimpleParameter):
    """Parameter type combining a trigger button and a LED status indicator.

    - Clicking the button emits ``sigActivated`` (same as the ``action`` type).
    - With ``checkable=True`` the button is a toggle: ``sigActivated`` is emitted each time it is pressed or released,
      and ``param.opts['checked']`` tells which one (set it with ``param.setOpts(checked=...)`` to change the button,
      for instance to release it when the action failed).
    - ``param.setValue(str)`` / ``param.value()`` controls the LED state by name.

    Options
    -------
    label : str, optional
        Text shown on the push button. Defaults to ``'▶'``.
    states : list of (str, str | QColor), list of str or 'status', optional
        Forwarded to :class:`~pymodaq_gui.utils.widgets.MultistateLED`.
        Defaults to the two-state red/green set. Give ``'status'``, or a list of names of the
        :class:`~pymodaq_gui.utils.status_palette.Status` workflow (e.g. ``[Status.OFF, Status.RUNNING,
        Status.IDLE, Status.ERROR]``), to get the colours of the :class:`~pymodaq_gui.utils.status_palette.StatusPalette`
        and to set the LED with ``param.setValue(Status.RUNNING)``.
    checkable : bool, optional
        The button stays pressed until it is pressed again. Defaults to ``False``.
    checked : bool, optional
        State of a checkable button. Defaults to ``False``.
    """

    itemClass = ActionLedParameterItem
    sigActivated = QtCore.Signal(object)

    def __init__(self, **opts):
        states = opts.get('states')
        if isinstance(states, (list, tuple)) and states and all(isinstance(state, str) for state in states):
            # names of the Status workflow: plain strings, so that the option can be saved in and read from xml
            opts['states'] = [state.value if isinstance(state, Enum) else str(state) for state in states]
        super().__init__(**opts)

    def _interpretValue(self, v):
        if isinstance(v, bool):
            warnings.warn(
                "ActionLedParameter value should be a state name string ('true'/'false'), "
                "not a bool. Bool support will be removed in a future version.",
                DeprecationWarning,
                stacklevel=2,
            )
            return LedState.TRUE if v else LedState.FALSE
        return str(v)

    def toggle(self, checked: bool):
        """The checkable button has been pressed or released"""
        self.opts['checked'] = bool(checked)
        self.activate()

    def activate(self):
        self.sigActivated.emit(self)
        self.emitStateChanged('activated', None)
