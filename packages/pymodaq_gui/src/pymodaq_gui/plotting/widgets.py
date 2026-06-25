# -*- coding: utf-8 -*-
"""
Created the 04/11/2022

@author: Sebastien Weber
"""

import pyqtgraph as pg
from qtpy import QtWidgets

from pymodaq_gui.plotting.utils.plot_utils import ViewBox
from pymodaq_gui.plotting.items.axis_scaled import AXIS_POSITIONS, AxisItemScaled

class PlotWidget(pg.PlotWidget):
    def __init__(self, *args, **kwargs):
        plot_item = pg.PlotItem(viewBox=ViewBox())
        super().__init__(*args, plotItem=plot_item, **kwargs)

    @property
    def view(self) -> ViewBox:
        return self.getViewBox()

    @property
    def legend(self):
        return self.plotItem.legend


class ImageWidget(PlotWidget):
    """this gives a layout to add imageitems.
    """

    def __init__(self, parent=None, *args_plotitem, **kwargs_plotitem):

        super().__init__(parent)
        self.setupUI(*args_plotitem, **kwargs_plotitem)

    def setAspectLocked(self, lock=True, ratio=1):
        """
        Defines the aspect ratio of the view
        Parameters
        ----------
        lock: (bool) if True aspect ratio is set to ratio, else the aspect ratio is varying when scaling the view
        ratio: (int) aspect ratio between horizontal and vertical axis
        """
        self.plotitem.vb.setAspectLocked(lock=True, ratio=1)

    def getAxis(self, position) -> AxisItemScaled:
        return self.plotitem.getAxis(position)

    def setupUI(self, *args_plotitem, **kwargs_plotitem):
        layout = QtWidgets.QGridLayout()
        # set viewer area
        self.scene_obj = self.scene()
        #self.view = View_cust()
        # self.plotitem = pg.PlotItem(viewBox=self.view, *args_plotitem, **kwargs_plotitem)
        # self.plotItem = self.plotitem  # for backcompatibility
        self.plotitem = self.plotItem

        self.setAspectLocked(lock=True, ratio=1)
        self.setCentralItem(self.plotitem)

    def add_scaled_axis(self, position):
        """
        Add a AxisItem_Scaled to the given position with respect with the plotitem
        Parameters
        ----------
        position: (str) either 'top', 'bottom', 'right' or 'left'

        Returns
        -------

        """
        if position not in AXIS_POSITIONS:
            raise ValueError(f'The Axis position {position} should be in {AXIS_POSITIONS}')
        axis = AxisItemScaled(position)
        self.plotitem.setAxisItems({position: axis})
        return axis


