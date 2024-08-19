from typing import Union

from qtpy import QtCore, QtWidgets
from qtpy.QtCore import QObject, Slot, Signal
import sys
import pyqtgraph as pg
import numpy as np
from easydict import EasyDict as edict

from pymodaq_gui.plotting.widgets import ImageWidget
from pymodaq_gui.plotting.data_viewers.viewer import ViewerBase
from pymodaq_data.data import DataRaw
from pymodaq_gui.plotting.items.image import UniformImageItem, SpreadImageItem


class Viewer2DBasic(ViewerBase):
    """Very Basic 2D Viewer used as a view to add Image Items into it and use the image object directly

    Not meant to plot directly data, see Viewer2D for that

    See Also
    --------
    Navigator, UniformImageItem, SpreadImageItem

    """

    def __init__(self, parent: QtWidgets.QWidget = None, **kwargs):
        super().__init__(parent, **kwargs)

        self.scaling_options = edict(scaled_xaxis=edict(label="", units=None, offset=0, scaling=1),
                                     scaled_yaxis=edict(label="", units=None, offset=0, scaling=1))
        self.setup_ui()

    def scale_axis(self, xaxis, yaxis):
        return xaxis * self.scaling_options.scaled_xaxis.scaling + self.scaling_options.scaled_xaxis.offset, yaxis * self.scaling_options.scaled_yaxis.scaling + self.scaling_options.scaled_yaxis.offset

    @Slot(float, float)
    def double_clicked(self, posx, posy):
        self.sig_double_clicked.emit(posx, posy)

    def setup_ui(self):
        vlayout = QtWidgets.QVBoxLayout()
        hsplitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        self.parent.setLayout(vlayout)
        vlayout.addWidget(hsplitter)

        self.image_widget = ImageWidget()
        hsplitter.addWidget(self.image_widget)

        self.scaled_xaxis = self.image_widget.add_scaled_axis('top')
        self.scaled_yaxis = self.image_widget.add_scaled_axis('right')
        # self.scaled_xaxis.linkToView(self.image_widget.view)
        # self.scaled_yaxis.linkToView(self.image_widget.view)

        # self.image_widget.plotitem.layout.addItem(self.scaled_xaxis, *(1, 1))
        # self.image_widget.plotitem.layout.addItem(self.scaled_yaxis, *(2, 2))

        self.image_widget.view.sig_double_clicked.connect(self.double_clicked)


        # histograms
        self.histo_widget = QtWidgets.QWidget()
        histo_layout = QtWidgets.QHBoxLayout()
        self.histo_widget.setLayout(histo_layout)
        self.histogram_red = pg.HistogramLUTWidget()
        self.histogram_green = pg.HistogramLUTWidget()
        self.histogram_blue = pg.HistogramLUTWidget()
        self.histogram_adaptive = pg.HistogramLUTWidget()
        Ntick = 3
        colors_red = [(int(r), 0, 0) for r in np.linspace(0, 255, Ntick)]
        colors_green = [(0, int(g), 0) for g in np.linspace(0, 255, Ntick)]
        colors_blue = [(0, 0, int(b)) for b in np.linspace(0, 255, Ntick)]
        colors_adaptive = [(int(b), int(b), int(b)) for b in np.linspace(0, 255, Ntick)]
        cmap_red = pg.ColorMap(pos=np.linspace(0.0, 1.0, Ntick), color=colors_red)
        cmap_green = pg.ColorMap(pos=np.linspace(0.0, 1.0, Ntick), color=colors_green)
        cmap_blue = pg.ColorMap(pos=np.linspace(0.0, 1.0, Ntick), color=colors_blue)
        cmap_adaptive = pg.ColorMap(pos=np.linspace(0.0, 1.0, Ntick), color=colors_adaptive)

        self.histogram_red.gradient.setColorMap(cmap_red)
        self.histogram_green.gradient.setColorMap(cmap_green)
        self.histogram_blue.gradient.setColorMap(cmap_blue)
        self.histogram_adaptive.gradient.setColorMap(cmap_adaptive)

        histo_layout.addWidget(self.histogram_red)
        histo_layout.addWidget(self.histogram_green)
        histo_layout.addWidget(self.histogram_blue)
        histo_layout.addWidget(self.histogram_adaptive)
        hsplitter.addWidget(self.histo_widget)

    def _show_data(self, data: DataRaw):
        """This basic viewer is not meant to plot data directly

        """
        ...

    def set_aspect_ratio(self, status=True):
        self.image_widget.plotitem.vb.setAspectLocked(lock=status, ratio=1)

    @property
    def plotitem(self):
        return self.image_widget.plotitem

    @property
    def histograms(self):
        return [self.histogram_red, self.histogram_green, self.histogram_blue]

    def add_image_item(self, image: Union[SpreadImageItem, UniformImageItem], histogram: pg.HistogramLUTWidget = None):
        """Adds an image item to this viewer plotitem

        Links it to an existing histogram
        """
        self.plotitem.addItem(image)
        if histogram in self.histograms:
            histogram.item.setImageItem(image)


if __name__ == '__main__':  # pragma: no cover
    from pymodaq_gui.plotting.items.image import SpreadImageItem
    from qtpy import QtSvg, QtGui

    app = QtWidgets.QApplication(sys.argv)
    form = QtWidgets.QWidget()
    prog = Viewer2DBasic(form)
    img = SpreadImageItem()
    prog.image_widget.plotItem.addItem(img)

    svg_item = QtSvg.QGraphicsSvgItem()
    svg_renderer = QtSvg.QSvgRenderer(
        r'C:\Users\weber\Labo\Projet-Dossier candidature\Technical project\GDSII\wafer.svg')
    svg_item.setSharedRenderer(svg_renderer)

    form.show()

    data = np.load('../../../resources/triangulation_data.npy')
    img.setImage(data)

    prog.image_widget.plotitem.addItem(svg_item)
    curr_size = svg_renderer.defaultSize()
    real_size = svg_item.boundingRect()
    # tr = QtGui.QTransform()
    # tr.translate(rect.left(), rect.top())
    # tr.scale(300/rect.width(), 300/rect.height())
    # svg_item.setTransform(tr)
    pass
    sys.exit(app.exec_())
