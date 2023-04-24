from collections.abc import Iterable

import copy
from numbers import Real, Number
from typing import List, Union
from typing import Iterable as IterableType

from easydict import EasyDict as edict
from multipledispatch import dispatch
import numpy as np
import pyqtgraph as pg
from qtpy import QtGui, QtCore, QtWidgets
from scipy.spatial import Delaunay as Triangulation

from pymodaq.utils import data as data_mod
from pymodaq.utils.plotting.items.axis_scaled import AxisItem_Scaled
from pymodaq.utils.plotting.data_viewers.viewer1Dbasic import Viewer1DBasic
from pymodaq.utils import daq_utils as utils
from pymodaq.utils.messenger import deprecation_msg


class Point:
    def __init__(self, *elt: IterableType[float]):
        """Initialize a geometric point in an arbitrary number of dimensions

        Parameters
        ----------
        elt: either a tuple of floats, passed as multiple parameters or a single Iterable parameter
        """
        if len(elt) == 1 and isinstance(elt[0], Iterable):
            elt = elt[0]

        self._coordinates = np.atleast_1d(np.squeeze(elt))
        self._ndim = len(elt)

    @property
    def coordinates(self):
        return self._coordinates

    def copy(self):
        return Point(self.coordinates.copy())

    def __getitem__(self, item: int):
        return self._coordinates[item]

    def __setitem__(self, key: int, value: float):
        self._coordinates[key] = value

    def __len__(self):
        return self._ndim

    def _compare_length(self, other: 'Point'):
        if len(self) != len(other):
            raise ValueError('Those points should be expressed in the same coordinate system and dimensions')

    def __add__(self, other: Union['Point', 'Vector']):
        self._compare_length(other)
        return Point(*(self._coordinates + other._coordinates))

    def __sub__(self, other: 'Point'):
        self._compare_length(other)
        return Point(*(self._coordinates - other._coordinates))

    def __repr__(self):
        return f'Point({self.coordinates})'


class Vector:
    def __init__(self, coordinates: Union[Point, np.ndarray], origin: Point = None):
        if isinstance(coordinates, Point):
            self._coordinates = coordinates.coordinates
        else:
            self._coordinates = coordinates

        if origin is None:
            origin = np.zeros((len(coordinates)))
        else:
            self._compare_length(origin)

        self._origin = origin

    def _compare_length(self, other: 'Point'):
        if len(self) != len(other):
            raise ValueError('Those Points/Vectors should be expressed in the same coordinate system and dimensions')

    @property
    def origin(self):
        return self._origin

    @property
    def coordinates(self):
        return self._coordinates

    def copy(self):
        return Vector(self.coordinates.copy(), origin=self.origin.copy())

    def __len__(self):
        return len(self._coordinates)

    def norm(self):
        return np.linalg.norm(self._coordinates)

    def unit_vector(self):
        return self * (1 / self.norm())

    def __add__(self, other: 'Vector'):
        self._compare_length(other)
        return Vector(self.coordinates + other.coordinates, origin=self.origin.copy())

    def __sub__(self, other: 'Vector'):
        self._compare_length(other)
        return Vector(self.coordinates - other.coordinates, origin=self.origin.copy())

    def __mul__(self, other: Number):
        if not isinstance(other, Number):
            raise TypeError(f'Cannot multiply a vector with {other}')
        return Vector(other * self.coordinates, origin=self.origin.copy())

    def dot(self, other: 'Vector'):
        self._compare_length(other)
        return np.dot(self.coordinates, other.coordinates)

    def cross(self, other: 'Vector'):
        self._compare_length(other)
        return np.cross(self.coordinates, other.coordinates)

    def __repr__(self):
        return f'Vector({self.coordinates})/Origin({self.origin.coordinates})'


def get_sub_segmented_positions(spacing: float, points: List[Point]) -> List[np.ndarray]:
    """Get Points coordinates spaced in between subsequent Points

    Parameters
    ----------
    spacing: float
        Distance between two subpoints
    points: List[Point]
        List of Points in arbitrary dimension forming segments one want to sample with a distance equal to spacing

    Returns
    -------
    List[np.ndarray]: The list of the coordinates of the points
    """
    positions = []
    for ind in range(len(points) - 1):
        vect = Vector(points[ind+1]-points[ind], origin=points[ind])
        npts = 0
        while npts * spacing < vect.norm():
            positions.append(
                (vect.origin + vect.unit_vector() * npts * spacing).coordinates)
            npts += 1

    # # add_last point not taken into account
    positions.append(points[-1].coordinates)
    return positions


class QVector(QtCore.QLineF):
    def __init__(self, *elt):
        super().__init__(*elt)

    def __repr__(self):
        return f"PyMoDAQ's QVector({self.x1()}, {self.y1()}, {self.x2()}, {self.y2()})"

    def __add__(self, qvect):
        v = QVector(self.x1() + qvect.x1(), self.y1() + qvect.y1(), self.x2() + qvect.x2(), self.y2() + qvect.y2())
        return v

    def __sub__(self, qvect):
        v = QVector(self.x1() - qvect.x1(), self.y1() - qvect.y1(), self.x2() - qvect.x2(), self.y2() - qvect.y2())
        return v

    def __mul__(self, coeff=float(1)):
        v = QVector(coeff * self.x1(), coeff * self.y1(), coeff * self.x2(), coeff * self.y2())
        return v

    def copy(self):
        vec = QVector()
        vec.setPoints(copy.copy(self.p1()), copy.copy(self.p2()))
        return vec

    def vectorize(self):
        v = QVector(QtCore.QPointF(0, 0), self.p2() - self.p1())
        return v

    def norm(self):
        return self.length()

    def unitVector(self):
        vec = self * (1 / self.length())
        return vec

    def normalVector(self):
        vec = self.vectorize()
        vec = QVector(0, 0, -vec.p2().y(), vec.p2().x())
        return vec

    def normalVector_not_vectorized(self):
        vec = self.vectorize()
        vec = QVector(0, 0, -vec.p2().y(), vec.p2().x())
        vec.translate(self.p1())
        return vec

    def dot(self, qvect):
        """
        scalar product
        """
        v1 = self.vectorize()
        v2 = qvect.vectorize()
        prod = v1.x2() * v2.x2() + v1.y2() * v2.y2()
        return prod

    def prod(self, qvect):
        """
        vectoriel product length along z
        """
        v1 = self.vectorize()
        v2 = qvect.vectorize()
        prod = v1.x2() * v2.y2() - v1.y2() * v2.x2()
        return prod

    def translate_to(self, point=QtCore.QPointF(0, 0)):
        vec = self + QVector(self.p1(), point)
        return vec


def makeAlphaTriangles(data, lut=None, levels=None, scale=None, useRGBA=False):
    """
    Convert an array of values into an ARGB array suitable for building QImages,
    OpenGL textures, etc.

    Returns the ARGB array (unsigned byte) and a boolean indicating whether
    there is alpha channel data. This is a two stage process:
        0) compute the polygons (triangles) from triangulation of the points
        1) Rescale the data based on the values in the *levels* argument (min, max).
        2) Determine the final output by passing the rescaled values through a
           lookup table.

    Both stages are optional.

    ============== ==================================================================================
    **Arguments:**
    data           numpy array of int/float types. If
    levels         List [min, max]; optionally rescale data before converting through the
                   lookup table. The data is rescaled such that min->0 and max->*scale*::

                      rescaled = (clip(data, min, max) - min) * (*scale* / (max - min))

                   It is also possible to use a 2D (N,2) array of values for levels. In this case,
                   it is assumed that each pair of min,max values in the levels array should be
                   applied to a different subset of the input data (for example, the input data may
                   already have RGB values and the levels are used to independently scale each
                   channel). The use of this feature requires that levels.shape[0] == data.shape[-1].
    scale          The maximum value to which data will be rescaled before being passed through the
                   lookup table (or returned if there is no lookup table). By default this will
                   be set to the length of the lookup table, or 255 if no lookup table is provided.
    lut            Optional lookup table (array with dtype=ubyte).
                   Values in data will be converted to color by indexing directly from lut.
                   The output data shape will be input.shape + lut.shape[1:].
                   Lookup tables can be built using ColorMap or GradientWidget.
    useRGBA        If True, the data is returned in RGBA order (useful for building OpenGL textures).
                   The default is False, which returns in ARGB order for use with QImage
                   (Note that 'ARGB' is a term used by the Qt documentation; the *actual* order
                   is BGRA).
    ============== ==================================================================================
    """
    points = data[:, :2]
    values = data[:, 2]

    profile = pg.debug.Profiler()
    if points.ndim not in (2,):
        raise TypeError("points must be 1D sequence of points")

    tri = Triangulation(points)
    tri_data = np.zeros((len(tri.simplices),))
    for ind, pts in enumerate(tri.simplices):
        tri_data[ind] = np.mean(values[pts])
    data = tri_data.copy()
    if lut is not None and not isinstance(lut, np.ndarray):
        lut = np.array(lut)

    if levels is None:
        # automatically decide levels based on data dtype
        if data.dtype.kind == 'u':
            levels = np.array([0, 2 ** (data.itemsize * 8) - 1])
        elif data.dtype.kind == 'i':
            s = 2 ** (data.itemsize * 8 - 1)
            levels = np.array([-s, s - 1])
        elif data.dtype.kind == 'b':
            levels = np.array([0, 1])
        else:
            raise Exception('levels argument is required for float input types')
    if not isinstance(levels, np.ndarray):
        levels = np.array(levels)
    if levels.ndim == 1:
        if levels.shape[0] != 2:
            raise Exception('levels argument must have length 2')
    elif levels.ndim == 2:
        if lut is not None and lut.ndim > 1:
            raise Exception('Cannot make ARGB data when both levels and lut have ndim > 2')
        if levels.shape != (data.shape[-1], 2):
            raise Exception('levels must have shape (data.shape[-1], 2)')
    else:
        raise Exception("levels argument must be 1D or 2D (got shape=%s)." % repr(levels.shape))

    profile()

    # Decide on maximum scaled value
    if scale is None:
        if lut is not None:
            scale = lut.shape[0] - 1
        else:
            scale = 255.

    # Decide on the dtype we want after scaling
    if lut is None:
        dtype = np.ubyte
    else:
        dtype = np.min_scalar_type(lut.shape[0] - 1)

    # Apply levels if given
    if levels is not None:
        if isinstance(levels, np.ndarray) and levels.ndim == 2:
            # we are going to rescale each channel independently
            if levels.shape[0] != data.shape[-1]:
                raise Exception(
                    "When rescaling multi-channel data, there must be the same number of levels as channels (data.shape[-1] == levels.shape[0])")
            newData = np.empty(data.shape, dtype=int)
            for i in range(data.shape[-1]):
                minVal, maxVal = levels[i]
                if minVal == maxVal:
                    maxVal += 1e-16
                newData[..., i] = pg.functions.rescaleData(data[..., i], scale / (maxVal - minVal), minVal, dtype=dtype)
            data = newData
        else:
            # Apply level scaling unless it would have no effect on the data
            minVal, maxVal = levels
            if minVal != 0 or maxVal != scale:
                if minVal == maxVal:
                    maxVal += 1e-16
                data = pg.functions.rescaleData(data, scale / (maxVal - minVal), minVal, dtype=dtype)

    profile()

    # apply LUT if given
    if lut is not None:
        data = pg.functions.applyLookupTable(data, lut)
    else:
        if data.dtype is not np.ubyte:
            data = np.clip(data, 0, 255).astype(np.ubyte)

    profile()

    # this will be the final image array
    imgData = np.empty((data.shape[0],) + (4,), dtype=np.ubyte)

    profile()

    # decide channel order
    if useRGBA:
        order = [0, 1, 2, 3]  # array comes out RGBA
    else:
        order = [2, 1, 0, 3]  # for some reason, the colors line up as BGR in the final image.

    # TODO check this
    # copy data into image array
    if data.ndim == 1:
        # This is tempting:
        #   imgData[..., :3] = data[..., np.newaxis]
        # ..but it turns out this is faster:
        for i in range(3):
            imgData[..., i] = data
    elif data.shape[1] == 1:
        for i in range(3):
            imgData[..., i] = data[..., 0]
    else:
        for i in range(0, data.shape[1]):
            imgData[..., i] = data[..., order[i]]

    profile()

    # add opaque alpha channel if needed
    if data.ndim == 1 or data.shape[1] == 3:
        alpha = False
        imgData[..., 3] = 255
    else:
        alpha = True

    profile()
    return tri, tri_data, imgData, alpha


def makePolygons(tri):
    polygons = []
    for seq in tri.points[tri.simplices]:
        polygons.append(QtGui.QPolygonF([QtCore.QPointF(*s) for s in seq] + [QtCore.QPointF(*seq[0])]))
    return polygons


class Data0DWithHistory:
    """Object to store scalar values and keep a history of a given length to them"""
    def __init__(self, Nsamples=200):
        super().__init__()
        self._datas = dict([])
        self._Nsamples = Nsamples
        self._xaxis = None
        self._data_length = 0

    @property
    def size(self):
        return self._data_length

    @property
    def length(self):
        return self._Nsamples

    @length.setter
    def length(self, history_length: int):
        if history_length > 0:
            self._Nsamples = history_length

    def __len__(self):
        return self.length

    @dispatch(data_mod.DataWithAxes)
    def add_datas(self, data: data_mod.DataRaw):
        datas = {data.labels[ind]: data.data[ind] for ind in range(len(data))}
        self.add_datas(datas)

    @dispatch(list)
    def add_datas(self, datas: list):
        """
        Add datas to the history
        Parameters
        ----------
        datas: (list) list of floats or np.array(float)
        """
        datas = {f'data_{ind:02d}': datas[ind] for ind in range(len(datas))}
        self.add_datas(datas)

    @dispatch(dict)
    def add_datas(self, datas: dict):
        """
        Add datas to the history on the form of a dict of key/data pairs (data is a numpy 0D array)
        Parameters
        ----------
        datas: (dict) dictionaary of floats or np.array(float)
        """
        if datas.keys() != self._datas.keys():
            self.clear_data()

        self._data_length += 1

        if self._data_length > self._Nsamples:
            self._xaxis += 1
        else:
            self._xaxis = np.linspace(0, self._data_length, self._data_length, endpoint=False)

        for data_key, data in datas.items():
            if not isinstance(data, np.ndarray):
                data = np.array([data])

            if self._data_length == 1:
                self._datas[data_key] = data
            else:
                self._datas[data_key] = np.concatenate((self._datas[data_key], data))

            if self._data_length > self._Nsamples:
                self._datas[data_key] = self._datas[data_key][1:]

    @property
    def datas(self):
        return self._datas

    @property
    def xaxis(self):
        return self._xaxis

    def clear_data(self):
        self._datas = dict([])
        self._data_length = 0
        self._xaxis = np.array([])


class View_cust(pg.ViewBox):
    """Custom ViewBox used to enable other properties compared to parent class: pg.ViewBox

    """
    sig_double_clicked = QtCore.Signal(float, float)

    def __init__(self, parent=None, border=None, lockAspect=False, enableMouse=True, invertY=False,
                 enableMenu=True, name=None, invertX=False):
        super().__init__(parent, border, lockAspect, enableMouse, invertY, enableMenu, name, invertX)

    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton and self.menuEnabled():
            ev.accept()
            self.raiseContextMenu(ev)
        if ev.double():
            pos = self.mapToView(ev.pos())
            self.sig_double_clicked.emit(pos.x(), pos.y())
