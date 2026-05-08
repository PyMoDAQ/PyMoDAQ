from qtpy.QtCore import Signal
from pyqtgraph.parametertree.parameterTypes.basetypes import WidgetParameterItem, SimpleParameter

from pymodaq_gui.utils.widgets import MultistateLED, DEFAULT_STATES


class _BoolLedWidget(MultistateLED):
    """MultistateLED with the bool-valued API that WidgetParameterItem expects."""

    sigChanged = Signal(bool)

    def __init__(self, readonly=True):
        super().__init__(states=DEFAULT_STATES, readonly=readonly)
        self.state_changed.connect(lambda name: self.sigChanged.emit(name == 'true'))

    def value(self):
        return self.get_state() == 'true'

    def setValue(self, v: bool):
        self.set_state('true' if v else 'false')


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
            states=opts.get('states', DEFAULT_STATES),
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

    def optsChanged(self, param, opts):
        super().optsChanged(param, opts)
        w = self.widget
        if 'states' in opts:
            w.set_states(opts['states'])
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


class MultistateLedParameter(SimpleParameter):
    """Parameter type displaying a named-state LED.

    Options
    -------
    states : list of (str, str | QColor), optional
        Forwarded to :class:`~pymodaq_gui.utils.widgets.MultistateLED`.
        Defaults to the two-state red/green set.
    """

    itemClass = MultistateLedParameterItem

    def _interpretValue(self, v):
        return str(v)
