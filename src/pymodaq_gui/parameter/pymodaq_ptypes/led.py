from pyqtgraph.parametertree.parameterTypes.basetypes import WidgetParameterItem, SimpleParameter
from pymodaq_gui.utils.widgets import QLED


class LedParameterItem(WidgetParameterItem):
    """Registered parameter type which displays a QLineEdit"""

    def makeWidget(self):
        w = QLED()
        w.clickable = False
        w.set_as_false()
        w.sigChanged = w.value_changed
        w.value = w.get_state
        w.setValue = w.set_as
        self.hideWidget = False
        return w


class LedPushParameterItem(LedParameterItem):
    """Registered parameter type which displays a QLineEdit"""

    def makeWidget(self):
        w = QLED()
        w.clickable = True
        w.set_as_false()
        w.sigChanged = w.value_changed
        w.value = w.get_state
        w.setValue = w.set_as
        self.hideWidget = False
        return w


class LedParameter(SimpleParameter):
    itemClass = LedParameterItem

    def _interpretValue(self, v):
        return bool(v)


class LedPushParameter(SimpleParameter):
    itemClass = LedPushParameterItem

    def _interpretValue(self, v):
        return bool(v)
