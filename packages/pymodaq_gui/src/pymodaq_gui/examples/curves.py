import sys

from pyqtgraph import functions as fn
from qtpy import QtCore, QtGui, QtWidgets
from pyqtgraph.graphicsItems.GraphicsObject import GraphicsObject

import numpy as np
from pymodaq_data import DataRaw, Axis, DataToExport

from pymodaq_gui.plotting.data_viewers.viewer2D import Viewer2D


class Curve(GraphicsObject):
    """
    **Bases:** :class:`GraphicsObject <pyqtgraph.GraphicsObject>`

    Item displaying an isocurve of a 2D array. To align this item correctly with an
    ImageItem, call ``isocurve.setParentItem(image)``.
    """

    def __init__(self, pen='w'):
        """
        Create a new isocurve item.

        ==============  ===============================================================
        **Arguments:**
        data            A 2-dimensional ndarray. Can be initialized as None, and set
                        later using :func:`setData <pyqtgraph.IsocurveItem.setData>`
        level           The cutoff value at which to draw the isocurve.
        pen             The color of the curve item. Can be anything valid for
                        :func:`mkPen <pyqtgraph.mkPen>`
        axisOrder       May be either 'row-major' or 'col-major'. By default this uses
                        the ``imageAxisOrder``
                        :ref:`global configuration option <apiref_config>`.
        ==============  ===============================================================
        """
        GraphicsObject.__init__(self)

        self.path: QtGui.QPainterPath = None
        self.pen: QtGui.QPen = None
        self.data = [(0, 3), (1, 2), (2, 4), (3.5, 0), (3.5, -1),]

        self.setPen(pen)

    def setData(self, data, level=None):
        """
        Set the data/image to draw isocurves for.

        ==============  ========================================================================
        **Arguments:**
        data            A 2-dimensional ndarray.
        level           The cutoff value at which to draw the curve. If level is not specified,
                        the previously set level is used.
        ==============  ========================================================================
        """

        self.data = data
        self.path = None
        self.prepareGeometryChange()
        self.update()

    def setPen(self, *args, **kwargs):
        """Set the pen used to draw the isocurve. Arguments can be any that are valid
        for :func:`mkPen <pyqtgraph.mkPen>`"""
        self.pen = fn.mkPen(*args, **kwargs)
        self.update()

    def setBrush(self, *args, **kwargs):
        """Set the brush used to draw the isocurve. Arguments can be any that are valid
        for :func:`mkBrush <pyqtgraph.mkBrush>`"""
        self.brush = fn.mkBrush(*args, **kwargs)
        self.update()

    def boundingRect(self):
        if self.data is None:
            return QtCore.QRectF()
        if self.path is None:
            self.generatePath()
        return self.path.boundingRect()

    def generatePath(self):
        self.path = QtGui.QPainterPath()
        self.path.moveTo(*self.data[0])
        for line in self.data[1:]:
            self.path.lineTo(*line)

    def paint(self, p, *args):
        if self.data is None:
            return
        if self.path is None:
            self.generatePath()
        p.setPen(self.pen)
        p.drawPath(self.path)


def main(data_distribution='uniform'):
    """either 'uniform' or 'spread'"""

    from pymodaq_gui.examples.curves import Curve

    app = QtWidgets.QApplication(sys.argv)
    widget = QtWidgets.QWidget()

    widget_button = QtWidgets.QWidget()
    widget_button.setLayout(QtWidgets.QHBoxLayout())
    button = QtWidgets.QPushButton('New Data')
    ndata = QtWidgets.QSpinBox()
    widget_button.layout().addWidget(button)
    widget_button.layout().addWidget(ndata)

    def print_data(data: DataToExport):
        print(data)
        print('******')
        print(data.get_data_from_dim('Data1D'))

    data_to_plot = generate_uniform_data()


    prog = Viewer2D(widget)
    widget.show()
    prog.data_to_export_signal.connect(print_data)

    prog.view.get_action('histo').trigger()
    prog.view.get_action('autolevels').trigger()

    prog.show_data(data_to_plot)

    prog.view.show_roi_target(True)
    prog.view.move_scale_roi_target((50, 40), (10, 20))

    prog.show_data(data_to_plot)

    curve = Curve()
    prog.view.plotitem.addItem(curve)
    unscaled_x, unscaled_y = prog.view.unscale_axis([d[0] for d in curve.data], [d[1] for d in curve.data])
    curve.setData(list(zip(unscaled_x, unscaled_y)))


    QtWidgets.QApplication.processEvents()
    sys.exit(app.exec_())


def generate_uniform_data() -> DataRaw:
    from pymodaq_utils.math_utils import gauss2D
    Nx = 100
    Ny = 2 * Nx
    data_random = np.random.normal(size=(Ny, Nx))
    x = 0.5 * np.linspace(-Nx / 2, Nx / 2 - 1, Nx)
    y = 0.2 * np.linspace(-Ny / 2, Ny / 2 - 1, Ny)
    data_red = 3 * np.sin(x / 5) ** 2 * gauss2D(x, 5, Nx / 10, y, -1, Ny / 10, 1, 90) + 0.2 * data_random
    data_green = 10 * gauss2D(x, -20, Nx / 10, y, -10, Ny / 20, 1, 0)
    data_green[70:80, 7:12] = np.nan

    data_to_plot = DataRaw(name='mydata', distribution='uniform',
                                   data=[data_red, data_green, data_red-data_green],
                                   labels = ['myreddata', 'mygreendata'],
                                   axes=[Axis('xaxis', units='xpxl', data=x, index=1),
                                         Axis('yaxis', units='ypxl', data=y, index=0), ])
    return data_to_plot



if __name__ == '__main__':
    main()