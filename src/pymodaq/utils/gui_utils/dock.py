import warnings

from qtpy.QtCore import Signal, QObject
from qtpy import QtGui, QtCore, QtWidgets
from pyqtgraph.dockarea import Dock, DockArea, DockLabel
from pyqtgraph.dockarea.DockArea import TempAreaWindow
from pyqtgraph.widgets.VerticalLabel import VerticalLabel


class VerticalLabel(VerticalLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def paintEvent(self, ev):
        p = QtGui.QPainter(self)
        # p.setBrush(QtGui.QBrush(QtGui.QColor(100, 100, 200)))
        # p.setPen(QtGui.QPen(QtGui.QColor(50, 50, 100)))
        # p.drawRect(self.rect().adjusted(0, 0, -1, -1))

        # p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255)))

        if self.orientation == 'vertical':
            p.rotate(-90)
            rgn = QtCore.QRect(-self.height(), 0, self.height(), self.width())
        else:
            rgn = self.contentsRect()
        align = self.alignment()
        # align  = QtCore.Qt.AlignmentFlag.AlignTop|QtCore.Qt.AlignmentFlag.AlignHCenter
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.hint = p.drawText(rgn, align, self.text())
        p.end()

        if self.orientation == 'vertical':
            self.setMaximumWidth(self.hint.height())
            self.setMinimumWidth(0)
            self.setMaximumHeight(16777215)
            if self.forceWidth:
                self.setMinimumHeight(self.hint.width())
            else:
                self.setMinimumHeight(0)
        else:
            self.setMaximumHeight(self.hint.height())
            self.setMinimumHeight(20)
            self.setMaximumWidth(16777215)
            if self.forceWidth:
                self.setMinimumWidth(self.hint.width())
            else:
                self.setMinimumWidth(0)


class DockLabel(VerticalLabel):

    sigClicked = QtCore.Signal(object, object)
    sigCloseClicked = QtCore.Signal()

    def __init__(self, text, closable=False, fontSize="12px"):
        self.dim = False
        self.fixedWidth = False
        self.fontSize = fontSize
        VerticalLabel.__init__(self, text, orientation='horizontal', forceWidth=True)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop|QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.dock = None
        self.updateStyle()
        self.setAutoFillBackground(False)
        self.mouseMoved = False

        self.closeButton = None
        if closable:
            self.closeButton = QtWidgets.QToolButton(self)
            self.closeButton.clicked.connect(self.sigCloseClicked)
            self.closeButton.setIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_TitleBarCloseButton))

    def updateStyle(self):
        r = '3px'
        if self.dim:
            fg = '#aaa'
            bg = '#44a'
            border = '#339'
        else:
            fg = '#fff'
            bg = '#66c'
            border = '#55B'

        if self.orientation == 'vertical':
            self.vStyle = """DockLabel {
                background-color : %s;
                color : %s;
                border-top-right-radius: 0px;
                border-top-left-radius: %s;
                border-bottom-right-radius: 0px;
                border-bottom-left-radius: %s;
                border-width: 0px;
                border-right: 2px solid %s;
                padding-top: 3px;
                padding-bottom: 3px;
                font-size: %s;
            }""" % (bg, fg, r, r, border, self.fontSize)
            self.setStyleSheet(self.vStyle)
        else:
            self.hStyle = """DockLabel {
                background-color : %s;
                color : %s;
                border-top-right-radius: %s;
                border-top-left-radius: %s;
                border-bottom-right-radius: 0px;
                border-bottom-left-radius: 0px;
                border-width: 0px;
                border-bottom: 2px solid %s;
                padding-left: 3px;
                padding-right: 3px;
                font-size: %s;
            }""" % (bg, fg, r, r, border, self.fontSize)
            self.setStyleSheet(self.hStyle)

    def setDim(self, d):
        if self.dim != d:
            self.dim = d
            self.updateStyle()

    def setOrientation(self, o):
        VerticalLabel.setOrientation(self, o)
        self.updateStyle()

    def isClosable(self):
        return self.closeButton is not None

    def mousePressEvent(self, ev):
        lpos = ev.position() if hasattr(ev, 'position') else ev.localPos()
        self.pressPos = lpos
        self.mouseMoved = False
        ev.accept()

    def mouseMoveEvent(self, ev):
        if not self.mouseMoved:
            lpos = ev.position() if hasattr(ev, 'position') else ev.localPos()
            self.mouseMoved = (lpos - self.pressPos).manhattanLength() > QtWidgets.QApplication.startDragDistance()

        if self.mouseMoved and ev.buttons() == QtCore.Qt.MouseButton.LeftButton:
            self.dock.startDrag()
        ev.accept()

    def mouseReleaseEvent(self, ev):
        ev.accept()
        if not self.mouseMoved:
            self.sigClicked.emit(self, ev)

    def mouseDoubleClickEvent(self, ev):
        if ev.button() == QtCore.Qt.MouseButton.LeftButton:
            self.dock.float()

    def resizeEvent (self, ev):
        if self.closeButton:
            if self.orientation == 'vertical':
                size = ev.size().width()
                pos = QtCore.QPoint(0, 0)
            else:
                size = ev.size().height()
                pos = QtCore.QPoint(ev.size().width() - size, 0)
            self.closeButton.setFixedSize(QtCore.QSize(size, size))
            self.closeButton.move(pos)
        super(DockLabel,self).resizeEvent(ev)


class Dock(Dock):
    dock_focused = Signal(str)
    def __init__(self, name, *args, **kwargs):
        label = DockLabel(name)
        super().__init__(name, *args, label=label, **kwargs)

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