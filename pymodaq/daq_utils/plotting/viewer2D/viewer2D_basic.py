from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QObject, pyqtSlot, QThread, pyqtSignal, QRectF, QRect, QPointF, QLocale
import sys
from collections import OrderedDict
import pyqtgraph as pg
import numpy as np
from easydict import EasyDict as edict


class Viewer2DBasic(QObject):
    sig_double_clicked = pyqtSignal(float, float)

    def __init__(self,parent=None, **kwargs):
        super(Viewer2DBasic,self).__init__()
        #setting the gui
        if parent is None:
            parent=QtWidgets.QWidget()
        self.parent = parent
        self.scaling_options = edict(scaled_xaxis=edict(label="",units=None,offset=0,scaling=1),scaled_yaxis=edict(label="",units=None,offset=0,scaling=1))
        self.setupUI()

    def scale_axis(self,xaxis,yaxis):
        return xaxis*self.scaling_options.scaled_xaxis.scaling+self.scaling_options.scaled_xaxis.offset,yaxis*self.scaling_options.scaled_yaxis.scaling+self.scaling_options.scaled_yaxis.offset

    @pyqtSlot(float,float)
    def double_clicked(self,posx,posy):
        self.sig_double_clicked.emit(posx,posy)

    def setupUI(self):
        vlayout = QtWidgets.QVBoxLayout()
        hsplitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        self.parent.setLayout(vlayout)
        vlayout.addWidget(hsplitter)
        self.ui = QObject()
        self.image_widget = ImageWidget()
        hsplitter.addWidget(self.image_widget)

        self.scaled_yaxis=AxisItem_Scaled('right')
        self.scaled_xaxis=AxisItem_Scaled('top')
        self.image_widget.plotitem.layout.addItem(self.scaled_xaxis, *(1,1))
        self.image_widget.plotitem.layout.addItem(self.scaled_yaxis, *(2,2))
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

class PlotCurveItem(pg.PlotCurveItem):

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.flipud = False
        self.fliplr = False
        self.flipudbis = False

    def paint(self, p, opt, widget):
        if self.xData is None or len(self.xData) == 0:
            return

        x = None
        y = None
        path = self.getPath()

        if self._exportOpts is not False:
            aa = self._exportOpts.get('antialias', True)
        else:
            aa = self.opts['antialias']

        p.setRenderHint(p.Antialiasing, aa)

        if self.opts['brush'] is not None and self.opts['fillLevel'] is not None:
            if self.fillPath is None:
                if x is None:
                    x, y = self.getData()
                p2 = QtGui.QPainterPath(self.path)
                p2.lineTo(x[-1], self.opts['fillLevel'])
                p2.lineTo(x[0], self.opts['fillLevel'])
                p2.lineTo(x[0], y[0])
                p2.closeSubpath()
                self.fillPath = p2

            p.fillPath(self.fillPath, self.opts['brush'])

        sp = pg.functions.mkPen(self.opts['shadowPen'])
        cp = pg.functions.mkPen(self.opts['pen'])

        self.setTransform(self.dataTransform())

        if sp is not None and sp.style() != QtCore.Qt.NoPen:
            p.setPen(sp)
            p.drawPath(path)
        p.setPen(cp)
        p.drawPath(path)

    def setOpts(self, update=True, **kargs):
        if 'flipud' in kargs:
            self.flipud = kargs['flipud']
        if 'fliplr' in kargs:
            self.fliplr = kargs['fliplr']
        if 'flipudbis' in kargs:
            self.flipudbis = kargs['flipudbis']
        if update:
            self.update()

    def dataTransform(self):
        """Return the transform that maps from this image's input array to its
        local coordinate system.

        This transform corrects for the transposition that occurs when image data
        is interpreted in row-major order.
        """
        # Might eventually need to account for downsampling / clipping here
        tr = QtGui.QTransform()
        if self.flipudbis:
            tr.scale(1, -1)
        if self.flipud:
            tr.scale(1, -1)
        if self.fliplr:
            tr.scale(-1, 1)
        return tr

class ImageItem(pg.ImageItem):
    def __init__(self, image=None, **kargs):
        super(ImageItem, self).__init__(image, **kargs)
        self.flipud = False
        self.fliplr = False
        self.rotate90 = False


    def getHistogram(self, bins='auto', step='auto', targetImageSize=200, targetHistogramSize=500, **kwds):
        """Returns x and y arrays containing the histogram values for the current image.
        For an explanation of the return format, see numpy.histogram().

        The *step* argument causes pixels to be skipped when computing the histogram to save time.
        If *step* is 'auto', then a step is chosen such that the analyzed data has
        dimensions roughly *targetImageSize* for each axis.

        The *bins* argument and any extra keyword arguments are passed to
        np.histogram(). If *bins* is 'auto', then a bin number is automatically
        chosen based on the image characteristics:

        * Integer images will have approximately *targetHistogramSize* bins,
          with each bin having an integer width.
        * All other types will have *targetHistogramSize* bins.

        This method is also used when automatically computing levels.
        """
        if self.image is None:
            return None, None
        if step == 'auto':
            step = (int(np.ceil(self.image.shape[0] / targetImageSize)),
                    int(np.ceil(self.image.shape[1] / targetImageSize)))
        if np.isscalar(step):
            step = (step, step)
        stepData = self.image[::step[0], ::step[1]]

        if bins == 'auto':
            try:
                if stepData.dtype.kind in "ui":
                    mn = stepData.min()
                    mx = stepData.max()
                    step = np.ceil((mx - mn) / 500.)
                    bins = np.arange(mn, mx + 1.01 * step, step, dtype=np.int)
                    if len(bins) == 0:
                        bins = [mn, mx]
            except:
                bins = 500
            else:
                bins = 500

        kwds['bins'] = bins
        stepData = stepData[np.isfinite(stepData)]
        hist = np.histogram(stepData, **kwds)

        return hist[1][:-1], hist[0]

    def setOpts(self, update=True, **kargs):
        if 'axisOrder' in kargs:
            val = kargs['axisOrder']
            if val not in ('row-major', 'col-major'):
                raise ValueError('axisOrder must be either "row-major" or "col-major"')
            self.axisOrder = val
        if 'flipud' in kargs:
            self.flipud = kargs['flipud']

        if 'fliplr' in kargs:
            self.fliplr = kargs['fliplr']
        if 'rotate90' in kargs:
            self.rotate90 = kargs['rotate90']

        if 'lut' in kargs:
            self.setLookupTable(kargs['lut'], update=update)
        if 'levels' in kargs:
            self.setLevels(kargs['levels'], update=update)
        #if 'clipLevel' in kargs:
            #self.setClipLevel(kargs['clipLevel'])
        if 'opacity' in kargs:
            self.setOpacity(kargs['opacity'])
        if 'compositionMode' in kargs:
            self.setCompositionMode(kargs['compositionMode'])
        if 'border' in kargs:
            self.setBorder(kargs['border'])
        if 'removable' in kargs:
            self.removable = kargs['removable']
            self.menu = None
        if 'autoDownsample' in kargs:
            self.setAutoDownsample(kargs['autoDownsample'])
        if update:
            self.update()

    def dataTransform(self):
        """Return the transform that maps from this image's input array to its
        local coordinate system.

        This transform corrects for the transposition that occurs when image data
        is interpreted in row-major order.
        """
        # Might eventually need to account for downsampling / clipping here
        tr = QtGui.QTransform()
        # if self.axisOrder == 'row-major':
        #     # transpose
        #     tr.scale(1, -1)
        #     tr.rotate(-90)
        if self.flipud or self.fliplr or self.rotate90:
            if self.rotate90:
                tr.translate(self.height() / 2, self.width() / 2)
            else:
                tr.translate(self.width() / 2, self.height() / 2)
        if self.flipud:
            tr.scale(1, -1)
        if self.fliplr:
            tr.scale(-1, 1)
        if self.rotate90:
            tr.rotate(90)
        if self.flipud or self.fliplr or self.rotate90:
            tr.translate(-self.width() / 2, -self.height() / 2)

        return tr

    def inverseDataTransform(self):
        """Return the transform that maps from this image's local coordinate
        system to its input array.

        See dataTransform() for more information.
        """
        tr = QtGui.QTransform()
        if self.axisOrder == 'row-major':
            # transpose
            tr.scale(1, -1)
            tr.rotate(-90)
        if self.flipud:
            tr.scale(1, -1)
        if self.fliplr:
            tr.scale(-1, 1)
        if self.rotate90:
            tr.rotate(90)
        return tr

    def paint(self, p, *args):
        if self.image is None:
            return
        if self.qimage is None:
            self.render()
            if self.qimage is None:
                return

        if self.paintMode is not None:
            p.setCompositionMode(self.paintMode)

        self.setTransform(self.dataTransform())

        shape = self.image.shape[:2] if self.axisOrder == 'col-major' else self.image.shape[:2][::-1]
        p.drawImage(QtCore.QRectF(0, 0, self.qimage.width(), self.qimage.height()), self.qimage)

        if self.border is not None:
            p.setPen(self.border)
            p.drawRect(self.boundingRect())

class ImageWidget(pg.GraphicsLayoutWidget):
    """this gives a layout to add imageitems.
    """
    def __init__(self, parent = None, *args_plotitem, **kwargs_plotitem):
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
        super(ImageWidget, self).__init__(parent)
        self.setupUI( *args_plotitem, **kwargs_plotitem)

    def setupUI(self,  *args_plotitem, **kwargs_plotitem):
        layout = QtWidgets.QGridLayout()
        #set viewer area
        self.scene_obj = self.scene()
        self.view = View_cust()
        self.plotitem = pg.PlotItem(viewBox=self.view,  *args_plotitem, **kwargs_plotitem)
        self.plotItem = self.plotitem #for backcompatibility
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


class AxisItem_Scaled(pg.AxisItem):
    """
    Subclass of pg.AxisItem enabling scaling of the tick values with respect to the linked viewbox
    """

    def __init__(self, orientation, scaling=1, offset=0, pen=None, linkView=None, parent=None, maxTickLength=-5,
                 showValues=True):
        """
        ==============  ===============================================================
        **Arguments:**
        orientation     one of 'left', 'right', 'top', or 'bottom'
        scaling         multiplicative coeff applied to the ticks
        offset          offset applied to the ticks after scaling
        maxTickLength   (px) maximum length of ticks to draw. Negative values draw
                        into the plot, positive values draw outward.
        linkView        (ViewBox) causes the range of values displayed in the axis
                        to be linked to the visible range of a ViewBox.
        showValues      (bool) Whether to display values adjacent to ticks
        pen             (QPen) Pen used when drawing ticks.
        ==============  ===============================================================
        """
        pg.AxisItem.__init__(self, orientation, pen, linkView, parent, maxTickLength, showValues)
        self.scaling = scaling
        self.offset = offset

    def linkedViewChanged(self, view, newRange=None):
        if self.orientation in ['right', 'left']:
            if newRange is None:
                newRange = [pos * self.scaling + self.offset for pos in view.viewRange()[1]]
            else:
                newRange = [pos * self.scaling + self.offset for pos in newRange]

            if view.yInverted():
                self.setRange(*newRange[::-1])
            else:
                self.setRange(*newRange)
        else:
            if newRange is None:
                newRange = [pos * self.scaling + self.offset for pos in view.viewRange()[0]]
            else:
                newRange = [pos * self.scaling + self.offset for pos in newRange]
            if view.xInverted():
                self.setRange(*newRange[::-1])
            else:
                self.setRange(*newRange)


if __name__ == '__main__':
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