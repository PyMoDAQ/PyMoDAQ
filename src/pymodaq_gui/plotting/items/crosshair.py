import os
import numpy as np
from qtpy import QtCore, QtGui
from qtpy.QtCore import Signal
import pyqtgraph as pg
import numpy as np


class Crosshair(pg.GraphicsObject):
    crosshair_dragged = Signal(float, float, name='crosshair_dragged')
    # signal used to pass crosshair position to other methods

    def __init__(self, plotitem, orientation='both', pen=None):
        super().__init__()
        
        if hasattr(plotitem, 'plotitem'):
            # in case one pass a plot or image widget
            self.plotitem = plotitem.plotitem
        else:
            self.plotitem = plotitem

        # self.crosshair_dragged[float,float].connect(self.print_pos) #exemple on how to use the crosshair_dragged signal
        if orientation == 'both':
            self.vline_visible = True
            self.hline_visible = True
        elif orientation == 'vertical':
            self.vline_visible = True
            self.hline_visible = False
        else:
            self.vline_visible = False
            self.hline_visible = True

        self.vLine = pg.InfiniteLine(angle=90, movable=True, pen=pen)
        self.hLine = pg.InfiniteLine(angle=0, movable=True, pen=pen)

        self.plotitem.addItem(self.vLine, ignoreBounds=True)
        self.plotitem.addItem(self.hLine, ignoreBounds=True)

        self.vLine.sigDragged.connect(self.update_hline)
        self.hLine.sigDragged.connect(self.update_vline)

    def show_hide_crosshair(self):
        if self.vline_visible:
            self.vLine.show()
        else:
            self.vLine.hide()
        if self.hline_visible:
            self.hLine.show()
        else:
            self.hLine.hide()

    def set_crosshair_position(self, xpos=0, ypos=0):
        self.vLine.setValue(xpos)
        self.hLine.setValue(ypos)
        self.crosshair_dragged.emit(xpos, ypos)

    def update_hline(self):
        self.hLine.sigDragged.disconnect(self.update_vline)
        p = self.vLine.getYPos() - self.vLine.cursorOffset[1]
        self.hLine.setPos(p)
        self.hLine.sigDragged.connect(self.update_vline)
        self.crosshair_dragged.emit(self.vLine.getXPos(), self.hLine.getYPos())

    def get_positions(self):
        return (self.vLine.getXPos(), self.hLine.getYPos())

    def update_vline(self):
        self.vLine.sigDragged.disconnect(self.update_hline)
        p = self.hLine.getXPos() - self.hLine.cursorOffset[0]
        self.vLine.setPos(p)
        self.vLine.sigDragged.connect(self.update_hline)
        self.crosshair_dragged.emit(self.vLine.getXPos(), self.hLine.getYPos())

    def hide(self):
        self.vLine.hide()
        self.hLine.hide()

    def show(self):
        self.show_hide_crosshair()

    def value(self):
        """
        value returns a tuple containing (x,y) positions of the crosshair
        """
        return (self.vLine.value(), self.hLine.value())

    def setVisible(self, state):
        self.hLine.setVisible(state)
        self.vLine.setVisible(state)
        if state:
            self.show_hide_crosshair()

    def isVisible(self):
        return self.hLine.isVisible()
