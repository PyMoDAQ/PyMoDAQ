import os
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
import pyqtgraph as pg
from pyqtgraph.graphicsItems.ImageItem import *
from pyqtgraph.graphicsItems.ROI import *
from pyqtgraph.graphicsItems.LinearRegionItem import *
from pyqtgraph.graphicsItems.InfiniteLine import *
from pyqtgraph.graphicsItems.ViewBox import *
from pyqtgraph.graphicsItems.GradientEditorItem import addGradientListToDocstring
import pyqtgraph.SignalProxy as SignalProxy
from pyqtgraph.Point import Point
import numpy as np

#class Signal_fromcrosshair(QObject):


class Crosshair(pg.GraphicsObject):

    crosshair_dragged=pyqtSignal(float, float, name='crosshair_dragged') #signal used to pass crosshair position to other methods

    def __init__(self,pyqtplot,orientation='both'):
        pg.GraphicsObject.__init__(self)
        self.pyqtplot=pyqtplot
        
        #self.crosshair_dragged[float,float].connect(self.print_pos) #exemple on how to use the crosshair_dragged signal
        if orientation=='both':
            self.vline_visible=True
            self.hline_visible=True
        elif orientation=='vertical':
            self.vline_visible=True
            self.hline_visible=False
        else:
            self.vline_visible=False
            self.hline_visible=True

        self.vLine = pg.InfiniteLine(angle=90, movable=True)
        self.hLine = pg.InfiniteLine(angle=0, movable=True)

        self.pyqtplot.addItem(self.vLine, ignoreBounds=True)
        self.pyqtplot.addItem(self.hLine, ignoreBounds=True)

        self.vLine.sigDragged.connect(self.update_hline)
        self.hLine.sigDragged.connect(self.update_vline)

    #vb = p1.vb
    #@pyqtSlot(float,float)
    #def print_pos(self,xpos,ypos):
    #    print(xpos)
    #    print(ypos)

    def show_hide_crosshair(self):
        if self.vline_visible:
            self.vLine.show()
        else:
            self.vLine.hide()
        if self.hline_visible:
            self.hLine.show()
        else:
            self.hLine.hide()

    def set_crosshair_position(self,xpos=0,ypos=0):
        self.vLine.setValue(xpos)
        self.hLine.setValue(ypos)

    def update_hline(self):
        self.hLine.sigDragged.disconnect(self.update_vline)
        p=self.vLine.getYPos()-self.vLine.cursorOffset[1]
        self.hLine.setPos(p)
        self.hLine.sigDragged.connect(self.update_vline)
        self.crosshair_dragged.emit(self.vLine.getXPos(),self.hLine.getYPos())

    def get_positions(self):
        return (self.vLine.getXPos(),self.hLine.getYPos())
    
    def update_vline(self):
        self.vLine.sigDragged.disconnect(self.update_hline)
        p=self.hLine.getXPos()-self.hLine.cursorOffset[0]
        self.vLine.setPos(p)
        self.vLine.sigDragged.connect(self.update_hline)
        self.crosshair_dragged.emit(self.vLine.getXPos(),self.hLine.getYPos())

    def hide(self):
        self.vLine.hide()
        self.hLine.hide()

    def show(self):
        self.show_hide_crosshair()

    def value(self):
        """
        value returns a tuple containing (x,y) positions of the crosshair
        """
        self.vLine.value()
        return (self.vLine.value(),self.hLine.value())

    def setVisible(self,state):
        self.hLine.setVisible(state)
        self.vLine.setVisible(state)
        if state:
            self.show_hide_crosshair()



## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    
    #generate layout
    app = QtGui.QApplication([])
    win = pg.GraphicsWindow()
    win.setWindowTitle('pyqtgraph example: crosshair')
    label = pg.LabelItem(justify='right')
    win.addItem(label)
    p1 = win.addPlot(row=1, col=0)
    p2 = win.addPlot(row=2, col=0)
    cross=Crosshair(p1)
    
    region = pg.LinearRegionItem()
    region.setZValue(10)
    # Add the LinearRegionItem to the ViewBox, but tell the ViewBox to exclude this 
    # item when doing auto-range calculations.
    p2.addItem(region, ignoreBounds=True)

    #pg.dbg()
    p1.setAutoVisible(y=True)


    #create numpy arrays
    #make the numbers large to show that the xrange shows data from 10000 to all the way 0
    data1 = 10000 + 15000 * pg.gaussianFilter(np.random.random(size=10000), 10) + 3000 * np.random.random(size=10000)
    data2 = 15000 + 15000 * pg.gaussianFilter(np.random.random(size=10000), 10) + 3000 * np.random.random(size=10000)

    p1.plot(data1, pen="r")
    p1.plot(data2, pen="g")

    p2.plot(data1, pen="w")

    def update():
        region.setZValue(10)
        minX, maxX = region.getRegion()
        p1.setXRange(minX, maxX, padding=0)    

    region.sigRegionChanged.connect(update)

    def updateRegion(window, viewRange):
        rgn = viewRange[0]
        region.setRegion(rgn)

    p1.sigRangeChanged.connect(updateRegion)

    region.setRegion([1000, 2000])
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
