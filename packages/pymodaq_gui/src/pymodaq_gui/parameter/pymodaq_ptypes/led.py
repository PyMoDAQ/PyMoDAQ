import warnings

from qtpy.QtCore import Signal
from pyqtgraph.parametertree.parameterTypes.basetypes import WidgetParameterItem, SimpleParameter

from pymodaq_gui.utils.widgets import MultistateLED, DEFAULT_STATES, LedState
from pymodaq_gui.utils.status_palette import StatusPalette
from pymodaq_utils.enums import StrEnum


def resolve_limits(limits):
    """Turn the ``limits`` option of a LED parameter into ``(name, color)`` pairs

    ``None`` gives the default two states, ``'status'`` all the states of the
    :class:`~pymodaq_gui.utils.status_palette.Status` workflow, a list of names (``Status`` members or the
    equivalent strings) the corresponding subset of it, coloured with the
    :class:`~pymodaq_gui.utils.status_palette.StatusPalette`; ``(name, color)`` pairs are used as they are.
    """
    if limits is None:
        return DEFAULT_STATES
    if isinstance(limits, str):
        if limits != 'status':
            raise ValueError(f"Unknown limits {limits!r}: use 'status', a list of names or (name, color) pairs")
        return StatusPalette.as_states()
    limits = list(limits)
    if limits and all(isinstance(state, str) for state in limits):
        return StatusPalette.subset(*limits)
    return limits


class _LedLimitsMixin:
    """The states of a LED parameter are its ``limits``; the former option ``states`` is deprecated"""

    def __init__(self, **opts):
        if 'states' in opts:
            self._warn_states()
            states = opts.pop('states')
            if opts.get('limits') is None:
                opts['limits'] = states
        limits = opts.get('limits')
        if isinstance(limits, (list, tuple)) and limits and all(isinstance(state, str) for state in limits):
            # names of the Status workflow: plain strings, so that the option can be saved in and read from xml
            opts['limits'] = [state.value if isinstance(state, StrEnum) else str(state) for state in limits]
        super().__init__(**opts)

    def setOpts(self, **opts):
        if 'states' in opts:
            self._warn_states()
            states = opts.pop('states')
            if 'limits' not in opts:
                opts['limits'] = states
        super().setOpts(**opts)

    @staticmethod
    def _warn_states():
        warnings.warn("The 'states' option of the LED parameters is deprecated, use 'limits'", DeprecationWarning,
                      stacklevel=3)


class _BoolLedWidget(MultistateLED):
    """MultistateLED with the bool-valued API that WidgetParameterItem expects."""

    sigChanged = Signal(bool)

    def __init__(self, readonly=True):
        super().__init__(states=DEFAULT_STATES, readonly=readonly)
        self.state_changed.connect(lambda name: self.sigChanged.emit(name == LedState.TRUE))

    def value(self):
        return self.get_state() == LedState.TRUE

    def setValue(self, v: bool):
        self.set_state(LedState.TRUE if v else LedState.FALSE)


class LedParameterItem(WidgetParameterItem):
    def makeWidget(self):
        w = _BoolLedWidget()
        w.clickable = False
        self.hideWidget = False
        return w


class LedPushParameterItem(WidgetParameterItem):
    def makeWidget(self):
        w = _BoolLedWidget()
        w.clickable = True
        self.hideWidget = False
        return w


class MultistateLedParameterItem(WidgetParameterItem):
    def makeWidget(self):
        opts = self.param.opts
        w = MultistateLED(
            states=resolve_limits(opts.get('limits')),
            gradient=opts.get('gradient', 'flat'),
            shape=opts.get('shape', 'circle'),
            size=opts.get('size', 20),
        )
        w.clickable = not opts.get('readonly', False)
        w.sigChanged = w.state_changed
        w.value = w.get_state
        w.setValue = w.set_state
        self.hideWidget = False
        return w

    def limitsChanged(self, param, limits):
        super().limitsChanged(param, limits)
        self.widget.set_states(resolve_limits(limits))
        try:
            self.widget.set_state(param.value())
        except ValueError:  # the current state is not one of the new ones
            pass

    def optsChanged(self, param, opts):
        super().optsChanged(param, opts)
        w = self.widget
        if 'gradient' in opts:
            w.set_gradient(opts['gradient'])
        if 'shape' in opts:
            w.set_shape(opts['shape'])
        if 'size' in opts:
            w.set_size(opts['size'])


class LedParameter(SimpleParameter):
    itemClass = LedParameterItem

    def _interpretValue(self, v):
        return bool(v)


class LedPushParameter(SimpleParameter):
    itemClass = LedPushParameterItem

    def _interpretValue(self, v):
        return bool(v)


class MultistateLedParameter(_LedLimitsMixin, SimpleParameter):
    """Parameter type displaying a named-state LED.

    Options
    -------
    limits : list of (str, str | QColor), list of str or 'status', optional
        The states of the LED, forwarded to :class:`~pymodaq_gui.utils.widgets.MultistateLED`.
        Defaults to the two-state red/green set. Give ``'status'``, or a list of names of the
        :class:`~pymodaq_gui.utils.status_palette.Status` workflow (e.g. ``[Status.OFF, Status.RUNNING,
        Status.IDLE, Status.ERROR]``), to get the colours of the :class:`~pymodaq_gui.utils.status_palette.StatusPalette`.
        Like the limits of any parameter, they can be changed with ``param.setLimits``.
    states :
        Deprecated, former name of ``limits``.
    """

    itemClass = MultistateLedParameterItem

    def _interpretValue(self, v):
        return str(v)
