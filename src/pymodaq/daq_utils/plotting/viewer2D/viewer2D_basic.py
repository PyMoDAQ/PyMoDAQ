from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QObject, pyqtSlot, QThread, pyqtSignal, QRectF, QRect, QPointF, QLocale
import sys
from ..plot_utils import AxisItem_Scaled
import pyqtgraph as pg
import numpy as np
from easydict import EasyDict as edict


class Viewer2DBasic(QObject):
    sig_double_clicked = pyqtSignal(float, float)

    def __init__(self, parent=None, **kwargs):
        super(Viewer2DBasic, self).__init__()
        # setting the gui
        if parent is None:
            parent = QtWidgets.QWidget()
        self.parent = parent
        self.scaling_options = edict(scaled_xaxis=edict(label="", units=None, offset=0, scaling=1),
                                     scaled_yaxis=edict(label="", units=None, offset=0, scaling=1))
        self.setupUI()

    def scale_axis(self, xaxis, yaxis):
        return xaxis * self.scaling_options.scaled_xaxis.scaling + self.scaling_options.scaled_xaxis.offset, yaxis * self.scaling_options.scaled_yaxis.scaling + self.scaling_options.scaled_yaxis.offset

    @pyqtSlot(float, float)
    def double_clicked(self, posx, posy):
        self.sig_double_clicked.emit(posx, posy)

    def setupUI(self):
        vlayout = QtWidgets.QVBoxLayout()
        hsplitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        self.parent.setLayout(vlayout)
        vlayout.addWidget(hsplitter)
        self.ui = QObject()
        self.image_widget = ImageWidget()
        hsplitter.addWidget(self.image_widget)

        self.scaled_yaxis = AxisItem_Scaled('right')
        self.scaled_xaxis = AxisItem_Scaled('top')
        self.image_widget.plotitem.layout.addItem(self.scaled_xaxis, *(1, 1))
        self.image_widget.plotitem.layout.addItem(self.scaled_yaxis, *(2, 2))
        self.image_widget.view.sig_double_clicked.connect(self.double_clicked)
        self.scaled_xaxis.linkToView(self.image_widget.view)
        self.scaled_yaxis.linkToView(self.image_widget.view)

        # histograms
        self.histo_widget = QtWidgets.QWidget()
        histo_layout = QtWidgets.QHBoxLayout()
        self.histo_widget.setLayout(histo_layout)
        self.histogram_red = pg.HistogramLUTWidget()
        self.histogram_green = pg.HistogramLUTWidget()
        self.histogram_blue = pg.HistogramLUTWidget()
        self.histogram_adaptive = pg.HistogramLUTWidget()
        Ntick = 3
        colors_red = [(int(r), 0, 0) for r in pg.np.linspace(0, 255, Ntick)]
        colors_green = [(0, int(g), 0) for g in pg.np.linspace(0, 255, Ntick)]
        colors_blue = [(0, 0, int(b)) for b in pg.np.linspace(0, 255, Ntick)]
        colors_adaptive = [(int(b), int(b), int(b)) for b in pg.np.linspace(0, 255, Ntick)]
        cmap_red = pg.ColorMap(pos=pg.np.linspace(0.0, 1.0, Ntick), color=colors_red)
        cmap_green = pg.ColorMap(pos=pg.np.linspace(0.0, 1.0, Ntick), color=colors_green)
        cmap_blue = pg.ColorMap(pos=pg.np.linspace(0.0, 1.0, Ntick), color=colors_blue)
        cmap_adaptive = pg.ColorMap(pos=pg.np.linspace(0.0, 1.0, Ntick), color=colors_adaptive)

        self.histogram_red.gradient.setColorMap(cmap_red)
        self.histogram_green.gradient.setColorMap(cmap_green)
        self.histogram_blue.gradient.setColorMap(cmap_blue)
        self.histogram_adaptive.gradient.setColorMap(cmap_adaptive)
        histo_layout.addWidget(self.histogram_red)
        histo_layout.addWidget(self.histogram_green)
        histo_layout.addWidget(self.histogram_blue)
        histo_layout.addWidget(self.histogram_adaptive)
        hsplitter.addWidget(self.histo_widget)


class ImageWidget(pg.GraphicsLayoutWidget):
    """this gives a layout to add imageitems.
    """

    def __init__(self, parent=None, *args_plotitem, **kwargs_plotitem):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(ImageWidget, self).__init__(parent)
        self.setupUI(*args_plotitem, **kwargs_plotitem)

    def setupUI(self, *args_plotitem, **kwargs_plotitem):
        layout = QtWidgets.QGridLayout()
        # set viewer area
        self.scene_obj = self.scene()
        self.view = View_cust()
        self.plotitem = pg.PlotItem(viewBox=self.view, *args_plotitem, **kwargs_plotitem)
        self.plotItem = self.plotitem  # for backcompatibility
        self.plotitem.vb.setAspectLocked(lock=True, ratio=1)
        self.setCentralItem(self.plotitem)


class View_cust(pg.ViewBox):
    """Custom ViewBox used to enable other properties compared to parent class: pg.ViewBox

    """
    sig_double_clicked = pyqtSignal(float, float)

    def __init__(self, parent=None, border=None, lockAspect=False, enableMouse=True, invertY=False,
                 enableMenu=True, name=None, invertX=False):
        super(View_cust, self).__init__(parent, border, lockAspect, enableMouse, invertY, enableMenu, name,
                                        invertX)

    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton and self.menuEnabled():
            ev.accept()
            self.raiseContextMenu(ev)
        if ev.double():
            pos = self.mapToView(ev.pos())
            self.sig_double_clicked.emit(pos.x(), pos.y())


if __name__ == '__main__':  # pragma: no cover
    from pymodaq.daq_utils.plotting.viewer2D.triangulationitem import TriangulationItem

    app = QtWidgets.QApplication(sys.argv)
    form = QtWidgets.QWidget()
    prog = Viewer2DBasic(form)
    img = TriangulationItem()
    prog.image_widget.plotItem.addItem(img)
    form.show()

    data = np.load('triangulation_data.npy')
    img.setImage(data)

    sys.exit(app.exec_())
