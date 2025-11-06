# -*- coding: utf-8 -*-
"""
Created the 06/01/2023

@author: Sebastien Weber
"""
import sys

import numpy as np

from qtpy import QtWidgets
from pymodaq_gui.plotting.data_viewers.viewer2D import Viewer2D
from pymodaq.utils.data import Axis, DataFromRoi, DataFromPlugins


def main():
    app = QtWidgets.QApplication(sys.argv)
    widget = QtWidgets.QWidget()

    Nx = 100
    Ny = 200
    data_random = np.random.normal(size=(Ny, Nx))
    x = np.linspace(-Nx/2, Nx/2 - 1, Nx)
    y = 0.2 * np.linspace(-Ny/2, Ny/2 - 1, Ny)

    from pymodaq.utils.math_utils import gauss2D

    data_red = 3 * np.sin(x/5)**2 * gauss2D(x, 5, Nx / 10,
                                            y, -1, Ny / 10, 1, 90) \
               + 0.1 * data_random
    data_green = 10 * gauss2D(x, -20, Nx / 10,
                              y, -10, Ny / 20, 1, 0)
    data_green[70:80, 7:12] = np.nan


    prog = Viewer2D(widget)
    widget.show()
    prog.show_data(DataFromPlugins(name='mydata', distribution='uniform', data=[data_red, data_green],
                                   axes=[Axis('xaxis', units='xpxl', data=x, index=1),
                                         Axis('yaxis', units='ypxl', data=y, index=0),]))

    prog.view.show_roi_target(True)
    prog.view.move_scale_roi_target((50, 40), (20, 20))

    QtWidgets.QApplication.processEvents()
    sys.exit(app.exec_())


if __name__ == '__main__':  # pragma: no cover
    main()
