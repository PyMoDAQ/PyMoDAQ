import warnings

from qtpy.QtCore import Signal, QObject
from qtpy import QtGui, QtCore, QtWidgets
from pyqtgraph.dockarea import Dock, DockArea, DockLabel
from pyqtgraph.dockarea.DockArea import TempAreaWindow
from pyqtgraph.widgets.VerticalLabel import VerticalLabel


class Dock(Dock):
    dock_focused = Signal(str)
    def __init__(self, name, *args, fontSize='20px', **kwargs):
        kwargs['fontSize'] = fontSize
        super().__init__(name, *args, **kwargs)

    def removeWidgets(self):
        for widget in self.widgets:
            self.layout.removeWidget(widget)
            widget.close()
        self.widgets = []

    def setOrientation(self, o='auto', force=False):
        """
        Sets the orientation of the title bar for this Dock.
        Must be one of 'auto', 'horizontal', or 'vertical'.
        By default ('auto'), the orientation is determined
        based on the aspect ratio of the Dock.
        """
        if self.container() is not None:  # patch here for when Dock is closed and when the QApplication
            # event loop is processed
            if o == 'auto' and self.autoOrient:
                if self.container().type() == 'tab':
                    o = 'horizontal'
                elif self.width() > self.height() * 1.5:
                    o = 'vertical'
                else:
                    o = 'horizontal'
            if force or self.orientation != o:
                self.orientation = o
                self.label.setOrientation(o)
                self.updateStyle()


class DockArea(DockArea, QObject):
    """
    Custom Dockarea class subclassing from the standard DockArea class and QObject so it can emit a signal when docks
    are moved around (one subclassed method: moveDock)
    See Also
    --------
    pyqtgraph.dockarea
    """
    dock_signal = Signal()

    def __init__(self, parent=None, temporary=False, home=None):
        super(DockArea, self).__init__(parent, temporary, home)

    def moveDock(self, dock, position, neighbor):
        """
        Move an existing Dock to a new location.
        """
        # Moving to the edge of a tabbed dock causes a drop outside the tab box
        if position in ['left', 'right', 'top',
                        'bottom'] and neighbor is not None and neighbor.container() is not None and neighbor.container().type() == 'tab':
            neighbor = neighbor.container()
        self.addDock(dock, position, neighbor)
        self.dock_signal.emit()

    def addTempArea(self):
        if self.home is None:
            area = DockArea(temporary=True, home=self)
            self.tempAreas.append(area)
            win = TempAreaWindow(area)
            area.win = win
            win.show()
        else:
            area = self.home.addTempArea()
        # print "added temp area", area, area.window()
        return area

