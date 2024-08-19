import collections

import numpy as np
import pyqtgraph as pg
from pymodaq_gui.plotting.utils.plot_utils import makeAlphaTriangles, makePolygons
from pyqtgraph import debug as debug, Point, functions as fn
from qtpy import QtCore, QtGui


class PymodaqImage(pg.ImageItem):
    def __init__(self, image=None, pen='r', **kargs):
        super().__init__(image, **kargs)
        self.flipud = False
        self.fliplr = False
        self.rotate90 = False
        self.rescale = None
        self.opts = {'pen': pen}

    def get_val_at(self, xy):
        """

        Parameters
        ----------
        xy: (tuple) containing x and y position of the point which you want the value

        Returns
        -------
        float: the value at the given position in the image
        """
        raise NotImplementedError


class UniformImageItem(PymodaqImage):
    def __init__(self, image=None, **kargs):
        super().__init__(image, **kargs)

    def get_val_at(self, xy):
        """

        Parameters
        ----------
        xy: (tuple) containing x and y position of the point which you want the value

        Returns
        -------
        float: the value at the given position in the image
        """
        return self.image[int(xy[1]), int(xy[0])]

    # def setRect(self, rect):
    #     """Scale and translate the image to fit within rect (must be a QRect or QRectF)."""
    #     self.resetTransform()
    #     self._dataTransform.translate(rect.left(), rect.top())
    #     self._dataTransform.scale(rect.width() / self.width(), rect.height() / self.height())


class SpreadImageItem(PymodaqImage):
    """
    **Bases:** :class:`GraphicsObject <pyqtgraph.GraphicsObject>`

    GraphicsObject displaying an image. Optimized for rapid update (ie video display).
    This item displays either a 2D numpy array (height, width) or
    a 3D array (height, width, RGBa). This array is optionally scaled (see
    :func:`setLevels <pyqtgraph.ImageItem.setLevels>`) and/or colored
    with a lookup table (see :func:`setLookupTable <pyqtgraph.ImageItem.setLookupTable>`)
    before being displayed.

    ImageItem is frequently used in conjunction with
    :class:`HistogramLUTItem <pyqtgraph.HistogramLUTItem>` or
    :class:`HistogramLUTWidget <pyqtgraph.HistogramLUTWidget>` to provide a GUI
    for controlling the levels and lookup table used to display the image.
    """

    def __init__(self, image=None, **kargs):
        """
        See :func:`setImage <pyqtgraph.ImageItem.setImage>` for all allowed initialization arguments.
        """
        super().__init__(image, **kargs)

        self.qimage = None
        self.triangulation = None
        self.tri_data = None
        self.mesh_pen = [255, 255, 255]

    def width(self):
        if self.image is None:
            return None
        return self.image[:, 0].max() - self.image[:, 0].min()

    def height(self):
        if self.image is None:
            return None
        return self.image[:, 1].max() - self.image[:, 1].min()

    def boundingRect(self):
        if self.image is None:
            return QtCore.QRectF(0., 0., 0., 0.)
        return QtCore.QRectF(self.image[:, 0].min(), self.image[:, 1].min(), float(self.width()), float(self.height()))

    def setImage(self, image=None, autoLevels=None, **kargs):
        """
        Update the image displayed by this item. For more information on how the image
        is processed before displaying, see :func:`makeARGB <pyqtgraph.makeARGB>`

        =================  =========================================================================
        **Arguments:**
        image             (numpy array) 2D array of: points coordinates (dim 0 is number of points)
                          (dim 1 is x, y coordinates and point value) image.shape = (N, 3)

                           Specifies the image data. May be 2D (width, height) or
                           3D (width, height, RGBa). The array dtype must be integer or floating
                           point of any bit depth. For 3D arrays, the third dimension must
                           be of length 3 (RGB) or 4 (RGBA). See *notes* below.

        autoLevels         (bool) If True, this forces the image to automatically select
                           levels based on the maximum and minimum values in the data.
                           By default, this argument is true unless the levels argument is
                           given.
        lut                (numpy array) The color lookup table to use when displaying the image.
                           See :func:`setLookupTable <pyqtgraph.ImageItem.setLookupTable>`.
        levels             (min, max) The minimum and maximum values to use when rescaling the image
                           data. By default, this will be set to the minimum and maximum values
                           in the image. If the image array has dtype uint8, no rescaling is necessary.
        opacity            (float 0.0-1.0)
        compositionMode    See :func:`setCompositionMode <pyqtgraph.ImageItem.setCompositionMode>`
        border             Sets the pen used when drawing the image border. Default is None.
        autoDownsample     (bool) If True, the image is automatically downsampled to match the
                           screen resolution. This improves performance for large images and
                           reduces aliasing.
        =================  =========================================================================


        **Notes:**

        For backward compatibility, image data is assumed to be in column-major order (column, row).
        However, most image data is stored in row-major order (row, column) and will need to be
        transposed before calling setImage()::

            imageitem.setImage(imagedata.T)

        This requirement can be changed by calling ``image.setOpts(axisOrder='row-major')`` or
        by changing the ``imageAxisOrder`` :ref:`global configuration option <apiref_config>`.


        """

        profile = debug.Profiler()

        gotNewData = False
        if image is None:
            if self.image is None:
                return
        else:
            self._xp = np
            gotNewData = True
            shapeChanged = (self.image is None or image.shape != self.image.shape)
            image = image.view(np.ndarray)
            if self.image is None or image.dtype != self.image.dtype:
                self._effectiveLut = None
            self.image = image
            if self.image.shape[0] > 2 ** 15 - 1:
                if 'autoDownsample' not in kargs:
                    kargs['autoDownsample'] = True
            if shapeChanged:
                self.prepareGeometryChange()
                self.informViewBoundsChanged()

        profile()

        if autoLevels is None:
            if 'levels' in kargs:
                autoLevels = False
            else:
                autoLevels = True
        if autoLevels:
            img = self.image
            while img.size > 2 ** 16:
                img = img[::2, ...]
            mn, mx = img[:, 2].min(), img[:, 2].max()
            if mn == mx:
                mn = 0
                mx = 255
            kargs['levels'] = [mn, mx]

        profile()

        self.setOpts(update=False, **kargs)

        profile()

        self.qimage = None
        self.update()

        profile()

        if gotNewData:
            self.sigImageChanged.emit()

    def get_val_at(self, xy):
        """

        Parameters
        ----------
        xy: (tuple) containing x and y position of the point which you want the value

        Returns
        -------
        flaot: the mean value of the three points surrounding the point
        """
        triangle_ind = self.triangulation.find_simplex(xy)
        val = np.mean(self.image[self.triangulation.simplices[triangle_ind]], axis=0)[2]
        return val

    def render(self):
        # Convert data to QImage for display.

        profile = debug.Profiler()
        if self.image is None or self.image.size == 0:
            return
        if isinstance(self.lut, collections.abc.Callable):
            lut = self.lut(self.image)
        else:
            lut = self.lut

        if self.autoDownsample:
            # reduce dimensions of image based on screen resolution
            o = self.mapToDevice(QtCore.QPointF(0, 0))
            x = self.mapToDevice(QtCore.QPointF(1, 0))
            y = self.mapToDevice(QtCore.QPointF(0, 1))
            w = Point(x - o).length()
            h = Point(y - o).length()
            if w == 0 or h == 0:
                self.qimage = None
                return
            xds = max(1, int(1.0 / w))
            yds = max(1, int(1.0 / h))
            axes = [1, 0] if self.axisOrder == 'row-major' else [0, 1]
            # TODO adapt downsample
            # image = fn.downsample(self.image, xds, axis=axes[0])
            # image = fn.downsample(image, yds, axis=axes[1])
            self._lastDownsample = (xds, yds)
        else:
            image = self.image

        # if the image data is a small int, then we can combine levels + lut
        # into a single lut for better performance
        levels = self.levels

        # Assume images are in column-major order for backward compatibility
        # (most images are in row-major order)

        self.triangulation, self.tri_data, rgba_values, alpha = makeAlphaTriangles(image, lut=lut, levels=levels,
                                                                                   useRGBA=True)
        polygons = makePolygons(self.triangulation)
        self.qimage = dict(polygons=polygons, values=rgba_values, alpha=alpha)

    def get_points_at(self, axis='x', val=0):
        """
        get all triangles values whose 'x' value is val or 'y' value is val
        1) compute triangle centroids
        2) set one of the coordinates as val
        3) check if this new point is still in the corresponding triangle
        4) if yes add point
        Parameters
        ----------
        axis: (str) either x or y if the set coordinates is x or y
        val: (float) the value of the x or y axis

        Returns
        -------
        ndarray: barycenter coordinates and triangles data values
        """
        if self.triangulation is None:
            self.render()
        centroids = self.compute_centroids()
        points_to_test = centroids.copy()
        if axis == 'x':
            points_to_test[:, 0] = val
        elif axis == 'y':
            points_to_test[:, 1] = val

        simplex = self.triangulation.find_simplex(points_to_test)
        good_indexes = np.where(simplex == np.linspace(0, len(simplex) - 1, len(simplex), dtype=int))
        return centroids[good_indexes[0]], self.tri_data[good_indexes[0]]

    def compute_centroids(self):
        return np.mean(self.triangulation.points[self.triangulation.simplices], axis=1)

    def dataTransform(self):
        """Return the transform that maps from this image's input array to its
        local coordinate system.

        This transform corrects for the transposition that occurs when image data
        is interpreted in row-major order.
        """
        # Might eventually need to account for downsampling / clipping here
        tr = QtGui.QTransform()
        if self.flipud:
            tr.scale(1, -1)
        if self.fliplr:
            tr.scale(-1, 1)
        if self.rotate90:
            tr.rotate(-90)
        return tr

    def setLookupTable(self, lut, update=True):
        super().setLookupTable(lut,update=update)
        if self.lut is not None and self.image is not None:
            lu = np.mean(self.lut(self.image), axis=0).astype(np.uint8)
            lu[lu > 0] = 255
            lu = list(lu)
        else:
            lu = [255, 255, 255]
        self.mesh_pen = lu

    def paint(self, p, *args):
        profile = debug.Profiler()
        if self.image is None:
            return
        if self.qimage is None:
            self.render()
            if self.qimage is None:
                return
            profile('render QImage')
        if self.paintMode is not None:
            p.setCompositionMode(self.paintMode)
            profile('set comp mode')

        self.setTransform(self.dataTransform())

        for pol, color in zip(self.qimage['polygons'], self.qimage['values']):

            p.setPen(fn.mkPen(*self.mesh_pen, 100, width=0.75))
            p.setBrush(fn.mkBrush(*color))
            p.drawPolygon(pol)

        profile('p.drawImage')
        if self.border is not None:
            p.setPen(self.border)
            p.drawRect(self.boundingRect())

    def save(self, fileName, *args):
        """Save this image to file. Note that this saves the visible image (after scale/color changes), not the original data."""
        pass

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
            step = int(np.ceil(self.image.shape[0] / targetImageSize))
        stepData = self.image[::step, 2:]

        if bins == 'auto':
            if stepData.dtype.kind in "ui":
                mn = stepData.min()
                mx = stepData.max()
                step = np.ceil((mx - mn) / 500.)
                bins = np.arange(mn, mx + 1.01 * step, step, dtype=np.int)
                if len(bins) == 0:
                    bins = [mn, mx]
            else:
                bins = 500

        kwds['bins'] = bins
        stepData = stepData[np.isfinite(stepData)]
        hist = np.histogram(stepData, **kwds)

        return hist[1][:-1], hist[0]

    def getPixmap(self):
        pass