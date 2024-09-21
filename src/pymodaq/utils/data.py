# -*- coding: utf-8 -*-
"""
Created the 28/10/2022

@author: Sebastien Weber
"""
from __future__ import annotations

from abc import ABCMeta, abstractmethod, abstractproperty
import numbers
import numpy as np
from typing import List, Tuple, Union, Any, Callable
from typing import Iterable as IterableType
from collections.abc import Iterable
from collections import OrderedDict
import logging

import warnings
from time import time
import copy
import pint
from multipledispatch import dispatch
import pymodaq
from pymodaq.utils.enums import BaseEnum, enum_checker
from pymodaq.utils.messenger import deprecation_msg
from pymodaq.utils.daq_utils import find_objects_in_list_from_attr_name_val
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.slicing import SpecialSlicersData
from pymodaq.utils import math_utils as mutils
from pymodaq.utils.config import Config
from pymodaq.utils.plotting.plotter.plotter import PlotterFactory

from pymodaq import Q_, ureg, Unit

config = Config()
plotter_factory = PlotterFactory()
logger = set_logger(get_module_name(__file__))


def check_units(units: str):
    try:
        Unit(units)
        return units
    except pint.errors.UndefinedUnitError:
        logger.warning(f'The unit "{units}" is not defined in the pint registry, switching to'
                       f'dimensionless')
    return ''


def squeeze(data_array: np.ndarray, do_squeeze=True, squeeze_indexes: Tuple[int]=None) -> np.ndarray:
    """ Squeeze numpy arrays return at least 1D arrays except if do_squeeze is False"""
    if do_squeeze:
        return np.atleast_1d(np.squeeze(data_array, axis=squeeze_indexes))
    else:
        return np.atleast_1d(data_array)


class DataIndexWarning(Warning):
    pass


class DataTypeWarning(Warning):
    pass


class DataDimWarning(Warning):
    pass


class DataSizeWarning(Warning):
    pass


WARNINGS = [DataIndexWarning, DataTypeWarning, DataDimWarning, DataSizeWarning]

if logging.getLevelName(logger.level) == 'DEBUG':
    for warning in WARNINGS:
        warnings.filterwarnings('default', category=warning)
else:
    for warning in WARNINGS:
        warnings.filterwarnings('ignore', category=warning)


class DataShapeError(Exception):
    pass


class DataLengthError(Exception):
    pass


class DataDimError(Exception):
    pass


class DataUnitError(Exception):
    pass


class DwaType(BaseEnum):
    DataWithAxes = 0
    DataRaw = 1
    DataActuator = 2
    DataFromPlugins = 3
    DataCalculated = 4


class DataDim(BaseEnum):
    """Enum for dimensionality representation of data"""
    Data0D = 0
    Data1D = 1
    Data2D = 2
    DataND = 3

    def __le__(self, other_dim: 'DataDim'):
        other_dim = enum_checker(DataDim, other_dim)
        return self.value.__le__(other_dim.value)

    def __lt__(self, other_dim: 'DataDim'):
        other_dim = enum_checker(DataDim, other_dim)
        return self.value.__lt__(other_dim.value)

    def __ge__(self, other_dim: 'DataDim'):
        other_dim = enum_checker(DataDim, other_dim)
        return self.value.__ge__(other_dim.value)

    def __gt__(self, other_dim: 'DataDim'):
        other_dim = enum_checker(DataDim, other_dim)
        return self.value.__gt__(other_dim.value)

    @property
    def dim_index(self):
       return self.value

    @staticmethod
    def from_data_array(data_array: np.ndarray):
        if len(data_array.shape) == 1 and data_array.size == 1:
            return DataDim['Data0D']
        elif len(data_array.shape) == 1 and data_array.size > 1:
            return DataDim['Data1D']
        elif len(data_array.shape) == 2:
            return DataDim['Data2D']
        else:
            return DataDim['DataND']


class DataSource(BaseEnum):
    """Enum for source of data"""
    raw = 0
    calculated = 1


class DataDistribution(BaseEnum):
    """Enum for distribution of data"""
    uniform = 0
    spread = 1


class Axis:
    """Object holding info and data about physical axis of some data

    In case the axis's data is linear, store the info as a scale and offset else store the data

    Parameters
    ----------
    label: str
        The label of the axis, for instance 'time' for a temporal axis
    units: str
        The units of the data in the object, for instance 's' for seconds
    data: ndarray
        A 1D ndarray holding the data of the axis
    index: int
        an integer representing the index of the Data object this axis is related to
    scaling: float
        The scaling to apply to a linspace version in order to obtain the proper scaling
    offset: float
        The offset to apply to a linspace/scaled version in order to obtain the proper axis
    size: int
        The size of the axis array (to be specified if data is None)
    spread_order: int
        An integer needed in the case where data has a spread DataDistribution. It refers to the index along the data's
        spread_index dimension

    Examples
    --------
    >>> axis = Axis('myaxis', units='seconds', data=np.array([1,2,3,4,5]), index=0)
    """

    base_type = 'Axis'

    def __init__(self, label: str = '', units: str = '', data: np.ndarray = None, index: int = 0,
                 scaling=None, offset=None, size=None, spread_order: int = 0):
        super().__init__()

        self.iaxis: Axis = SpecialSlicersData(self, False)

        self._size = size
        self._data = None
        self._index = None
        self._label = None
        self._units = None
        self._scaling = scaling
        self._offset = offset

        self.units = units
        self.label = label
        self.data = data
        self.index = index
        self.spread_order = spread_order
        if (scaling is None or offset is None or size is None) and data is not None:
            self.get_scale_offset_from_data(data)

    def copy(self):
        return copy.copy(self)

    def as_dwa(self) -> DataWithAxes:
        dwa = DataRaw(self.label, data=[self.get_data()],
                      labels=[f'{self.label}_{self.units}'])
        dwa.create_missing_axes()
        return dwa

    @property
    def label(self) -> str:
        """str: get/set the label of this axis"""
        return self._label

    @label.setter
    def label(self, lab: str):
        if not isinstance(lab, str):
            raise TypeError('label for the Axis class should be a string')
        self._label = lab

    @property
    def units(self) -> str:
        """str: get/set the units for this axis"""
        return self._units

    @units.setter
    def units(self, units: str):
        if not isinstance(units, str):
            raise TypeError('units for the Axis class should be a string')
        units = check_units(units)
        self._units = units

    @property
    def index(self) -> int:
        """int: get/set the index this axis corresponds to in a DataWithAxis object"""
        return self._index

    @index.setter
    def index(self, ind: int):
        self._check_index_valid(ind)
        self._index = ind

    @property
    def data(self):
        """np.ndarray: get/set the data of Axis"""
        return self._data

    @data.setter
    def data(self, data: np.ndarray):
        if data is not None:
            self._check_data_valid(data)
            self.get_scale_offset_from_data(data)
            self._size = data.size
        elif self.size is None:
            self._size = 0
        self._data = data

    def get_data(self) -> np.ndarray:
        """Convenience method to obtain the axis data (usually None because scaling and offset are used)"""
        return self._data if self._data is not None else self._linear_data(self.size)

    def get_data_at(self, indexes: Union[int, IterableType, slice]) -> np.ndarray:
        """ Get data at specified indexes

        Parameters
        ----------
        indexes:
        """
        if not (isinstance(indexes, np.ndarray) or isinstance(indexes, slice) or
                isinstance(indexes, int)):
            indexes = np.array(indexes)
        return self.get_data()[indexes]

    def get_scale_offset_from_data(self, data: np.ndarray = None):
        """Get the scaling and offset from the axis's data

        If data is not None, extract the scaling and offset

        Parameters
        ----------
        data: ndarray
        """
        if data is None and self._data is not None:
            data = self._data

        if self.is_axis_linear(data):
            if len(data) == 1:
                self._scaling = 1
            else:
                self._scaling = np.mean(np.diff(data))
            self._offset = data[0]
            self._data = None

    def is_axis_linear(self, data=None):
        if data is None:
            data = self.get_data()
        if data is not None:
            return np.allclose(np.diff(data), np.mean(np.diff(data)))
        else:
            return False

    @property
    def scaling(self):
        return self._scaling

    @scaling.setter
    def scaling(self, _scaling: float):
        self._scaling = _scaling

    @property
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, _offset: float):
        self._offset = _offset

    @property
    def size(self) -> int:
        """int: get/set the size/length of the 1D ndarray"""
        return self._size

    @size.setter
    def size(self, _size: int):
        if self._data is None:
            self._size = _size

    @staticmethod
    def _check_index_valid(index: int):
        if not isinstance(index, int):
            raise TypeError('index for the Axis class should be a positive integer')
        elif index < 0:
            raise ValueError('index for the Axis class should be a positive integer')

    @staticmethod
    def _check_data_valid(data):
        if not isinstance(data, np.ndarray):
            raise TypeError(f'data for the Axis class should be a 1D numpy array')
        elif len(data.shape) != 1:
            raise ValueError(f'data for the Axis class should be a 1D numpy array')

    def _linear_data(self, nsteps: int):
        """create axis data with a linear version using scaling and offset"""
        return self._offset + self._scaling * np.linspace(0, nsteps-1, nsteps)

    def create_linear_data(self, nsteps:int):
        """replace the axis data with a linear version using scaling and offset"""
        self.data = self._linear_data(nsteps)

    @staticmethod
    def create_simple_linear_data(nsteps: int):
        return np.linspace(0, nsteps-1, nsteps)

    def __len__(self):
        return self.size

    def _compute_slices(self, slices, *ignored, **ignored_also):
        return slices

    def _slicer(self, _slice, *ignored, **ignored_also):
        ax: Axis = copy.deepcopy(self)
        if isinstance(_slice, int):
            ax.data = np.array([ax.get_data()[_slice]])
            return ax
        elif _slice is Ellipsis:
            return ax
        elif isinstance(_slice, slice):
            if ax._data is not None:
                ax.data = ax._data.__getitem__(_slice)
                return ax
            else:
                start = _slice.start if _slice.start is not None else 0
                stop = _slice.stop if _slice.stop is not None else self.size

                ax._offset = ax.offset + start * ax.scaling
                ax._size = stop - start
                return ax

    def __getitem__(self, item):
        if hasattr(self, item):
            # for when axis was a dict
            deprecation_msg('attributes from an Axis object should not be fetched using __getitem__')
            return getattr(self, item)

    def __repr__(self):
        return f'{self.__class__.__name__}: <label: {self.label}> - <units: {self.units}> - <index: {self.index}>'

    def __mul__(self, scale: numbers.Real):
        if isinstance(scale, numbers.Real):
            ax = copy.deepcopy(self)
            if self.data is not None:
                ax.data *= scale
            else:
                ax._offset *= scale
                ax._scaling *= scale
            return ax

    def __add__(self, offset: numbers.Real):
        if isinstance(offset, numbers.Real):
            ax = copy.deepcopy(self)
            if self.data is not None:
                ax.data += offset
            else:
                ax._offset += offset
            return ax

    def __eq__(self, other: Axis):
        if isinstance(other, Axis):
            eq = self.label == other.label
            eq = eq and (Unit(self.units).is_compatible_with(other.units))
            eq = eq and (self.index == other.index)
            if self.data is not None and other.data is not None:
                eq = eq and (np.allclose(Q_(self.data, self.units),
                                         Q_(other.data, other.units)))
            else:
                eq = eq and (np.allclose(Q_(self.offset, self.units),
                                         Q_(other.offset, other.units)))
                eq = eq and (np.allclose(Q_(self.scaling, self.units),
                                         Q_(other.scaling, other.units)))

            return eq
        else:
            return False

    def mean(self):
        if self._data is not None:
            return np.mean(self._data)
        else:
            return self.offset + self.size / 2 * self.scaling

    def min(self):
        if self._data is not None:
            return np.min(self._data)
        else:
            return self.offset + (self.size * self.scaling if self.scaling < 0 else 0)

    def max(self):
        if self._data is not None:
            return np.max(self._data)
        else:
            return self.offset + (self.size * self.scaling if self.scaling > 0 else 0)

    def find_index(self, threshold: float) -> int:
        """find the index of the threshold value within the axis"""
        if threshold < self.min():
            return 0
        elif threshold > self.max():
            return len(self) - 1
        elif self._data is not None:
            return mutils.find_index(self._data, threshold)[0][0]
        else:
            return int((threshold - self.offset) / self.scaling)

    def find_indexes(self, thresholds: IterableType[float]) -> IterableType[int]:
        if isinstance(thresholds, numbers.Number):
            thresholds = [thresholds]
        return [self.find_index(threshold) for threshold in thresholds]


class NavAxis(Axis):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        deprecation_msg('NavAxis should not be used anymore, please use Axis object with correct index.'
                        'The navigation index should be specified in the Data object')


class DataLowLevel:
    """Abstract object for all Data Object

    Parameters
    ----------
    name: str
        the identifier of the data

    Attributes
    ----------
    name: str
    timestamp: float
        Time in seconds since epoch. See method time.time()
    """

    def __init__(self, name: str):
        self._timestamp = time()
        self._name = name

    @property
    def name(self):
        """Get/Set the identifier of the data"""
        return self._name

    @name.setter
    def name(self, other_name: str):
        self._name = other_name

    @property
    def timestamp(self):
        """Get/Set the timestamp of when the object has been created"""
        return self._timestamp

    @timestamp.setter
    def timestamp(self, timestamp: float):
        """The timestamp of when the object has been created"""
        self._timestamp = timestamp


class DataBase(DataLowLevel):
    """Base object to store homogeneous data and metadata generated by pymodaq's objects.

    To be inherited for real data

    Parameters
    ----------
    name: str
        the identifier of these data
    source: DataSource or str
        Enum specifying if data are raw or processed (for instance from roi)
    dim: DataDim or str
        The identifier of the data type
    distribution: DataDistribution or str
        The distribution type of the data: uniform if distributed on a regular grid or spread if on
        specific unordered points
    data: list of ndarray
        The data the object is storing
    labels: list of str
        The labels of the data nd-arrays
    origin: str
        An identifier of the element where the data originated, for instance the DAQ_Viewer's name.
        Used when appending DataToExport in DAQ_Scan to disintricate from which origin data comes
        from when scanning multiple detectors.
    units: str
        A unit string identifier as specified in the UnitRegistry of the pint module

    kwargs: named parameters
        All other parameters are stored dynamically using the name/value pair. The name of these
        extra parameters are added into the extra_attributes attribute

    Attributes
    ----------
    name: str
        the identifier of these data
    source: DataSource or str
        Enum specifying if data are raw or processed (for instance from roi)
    dim: DataDim or str
        The identifier of the data type
    distribution: DataDistribution or str
        The distribution type of the data: uniform if distributed on a regular grid or spread if on specific
        unordered points
    data: list of ndarray
        The data the object is storing
    labels: list of str
        The labels of the data nd-arrays
    origin: str
        An identifier of the element where the data originated, for instance the DAQ_Viewer's name. Used when appending
        DataToExport in DAQ_Scan to disintricate from which origin data comes from when scanning multiple detectors.
    shape: Tuple[int]
        The shape of the underlying data
    size: int
        The size of the ndarrays stored in the object
    length: int
        The number of ndarrays stored in the object
    extra_attributes: List[str]
        list of string giving identifiers of the attributes added dynamically at the initialization (for instance
        to save extra metadata using the DataSaverLoader

    See Also
    --------
    DataWithAxes, DataFromPlugins, DataRaw, DataSaverLoader

    Examples
    --------
    >>> import numpy as np
    >>> from pymodaq.utils.data import DataBase, DataSource, DataDim, DataDistribution
    >>> data = DataBase('mydata', source=DataSource['raw'], dim=DataDim['Data1D'], \
    distribution=DataDistribution['uniform'], data=[np.array([1.,2.,3.]), np.array([4.,5.,6.])],\
    labels=['channel1', 'channel2'], origin='docutils code')
    >>> data.dim
    <DataDim.Data1D: 1>
    >>> data.source
    <DataSource.raw: 0>
    >>> data.shape
    (3,)
    >>> data.length
    2
    >>> data.size
    3
    """

    base_type = 'Data'

    def __init__(self, name: str,
                 source: DataSource = None, dim: DataDim = None,
                 distribution: DataDistribution = DataDistribution['uniform'],
                 data: List[np.ndarray] = None,
                 labels: List[str] = None, origin: str = '',
                 units: str = '',
                 **kwargs):

        super().__init__(name=name)
        self._iter_index = 0
        self._shape = None
        self._size = None
        self._data = None
        self._length = None
        self._labels = None
        self._dim = dim
        self._units = check_units(units)
        self._errors = None
        self.origin = origin

        source = enum_checker(DataSource, source)
        self._source = source

        distribution = enum_checker(DataDistribution, distribution)
        self._distribution = distribution

        self.data = data  # dim consistency is actually checked within the setter method

        self._check_labels(labels)
        self.extra_attributes = []
        self.add_extra_attribute(**kwargs)

    @property
    def units(self):
        """ Get/Set the object units

        Setting to other units should retain the unit compatibility
        """
        return self._units

    @units.setter
    def units(self, units: str):
        units = check_units(units)
        self.units_as(units, inplace=True)

    def force_units(self, units: str):
        """ Change immediately the units to whatever else. Use this with care!"""
        self._units = units

    def units_as(self, units: str, inplace=True) -> 'DataBase':
        """ Set the object units to the new one (if possible)

        Parameters
        ----------
        units: str
            The new unit to convert the data to
        inplace: bool
            default True.
            If True replace the data's arrays by array in the new units
            If False, return a new data object
        """
        arrays = []
        try:
            for ind_array in range(len(self)):
                arrays.append(self.quantities[ind_array].m_as(units))

        except pint.errors.DimensionalityError as e:
            raise DataUnitError(
                f'Cannot change the Data units to {units} \n'
                f'{e}')

        if inplace:
            self.data = arrays
            self._units = units
            return self
        else:
            new_data = copy.deepcopy(self)
            new_data.data = arrays
            new_data._units = units
            return new_data

    def as_dte(self, name: str = 'mydte') -> DataToExport:
        """Convenience method to wrap the DataWithAxes object into a DataToExport"""
        return DataToExport(name, data=[self])

    def add_extra_attribute(self, **kwargs):
        for key in kwargs:
            if key not in self.extra_attributes:
                self.extra_attributes.append(key)
            setattr(self, key, kwargs[key])

    def get_full_name(self) -> str:
        """Get the data ful name including the origin attribute into the returned value

        Returns
        -------
        str: the name of the ataWithAxes data constructed as : origin/name

        Examples
        --------
        d0 = DataBase(name='datafromdet0', origin='det0')
        """
        return f'{self.origin}/{self.name}'

    def __repr__(self):
        return (f'{self.__class__.__name__} <{self.name}> '
                f'<u: {self.units}> '
                f'<{self.dim}> <{self.source}> <{self.shape}>')

    def __len__(self):
        return self.length

    def __iter__(self):
        self._iter_index = 0
        return self

    def __next__(self):
        if self._iter_index < len(self):
            self._iter_index += 1
            return self.data[self._iter_index-1]
        else:
            raise StopIteration

    def __getitem__(self, item) -> np.ndarray:
        if (isinstance(item, int) and item < len(self)) or isinstance(item, slice):
            return self.data[item]
        else:
            raise IndexError(f'The index should be an integer lower than the data length')

    def __setitem__(self, key, value):
        if isinstance(key, int) and key < len(self) and isinstance(value, np.ndarray) and value.shape == self.shape:
            self.data[key] = value
        else:
            raise IndexError(f'The index should be an positive integer lower than the data length')

    def __add__(self, other: object):
        if isinstance(other, DataBase) and len(other) == len(self):
            new_data = copy.deepcopy(self)
            for ind_array in range(len(new_data)):
                if self[ind_array].shape != other[ind_array].shape:
                    raise ValueError('The shapes of arrays stored into the data are not consistent')
                try:
                    new_data[ind_array] = (Q_(self[ind_array], self.units) +
                                           Q_(other[ind_array], other.units)).m_as(self.units)
                except pint.errors.DimensionalityError as e:
                    raise DataUnitError(
                        f'Cannot sum Data objects not having the same dimension: {e}')
            return new_data
        elif isinstance(other, numbers.Number) and self.length == 1 and self.size == 1:
            new_data = copy.deepcopy(self)
            new_data = new_data + DataActuator(data=other)
            return new_data
        else:
            raise TypeError(f'Could not add a {other.__class__.__name__} or a {self.__class__.__name__} '
                            f'of a different length')

    def __sub__(self, other: object):
        return self.__add__(other * -1)
        #
        # if isinstance(other, DataBase) and len(other) == len(self):
        #     new_data = copy.deepcopy(self)
        #     for ind_array in range(len(new_data)):
        #         new_data[ind_array] = self[ind_array] - other[ind_array]
        #     return new_data
        # elif isinstance(other, numbers.Number) and self.length == 1 and self.size == 1:
        #     new_data = copy.deepcopy(self)
        #     new_data = new_data - DataActuator(data=other)
        #     return new_data
        # else:
        #     raise TypeError(f'Could not substract a {other.__class__.__name__} or a {self.__class__.__name__} '
        #                     f'of a different length')

    def __mul__(self, other):
        if (isinstance(other, numbers.Number) or
                (isinstance(other, np.ndarray) and other.shape == self._shape)):
            new_data = copy.deepcopy(self)
            for ind_array in range(len(new_data)):
                new_data[ind_array] = self[ind_array] * other
            return new_data
        elif isinstance(other, DataBase) and other.shape == self._shape:
            new_data = copy.deepcopy(self)
            new_unit = str((Q_(self[0], self.units) *
                           Q_(other[0], other.units)).to_base_units().units)
            for ind_array in range(len(new_data)):
                new_data[ind_array] = \
                    ((Q_(self[ind_array], self.units) * Q_(other[ind_array], other.units))
                     .to_base_units()).magnitude
            new_data._units = new_unit
            return new_data
        else:
            raise TypeError(f'Could not multiply a {other.__class__.__name__} and a {self.__class__.__name__} '
                            f'of a different length')

    def __truediv__(self, other):
        if isinstance(other, numbers.Number):
            return self * (1 / other)
        else:
            raise TypeError(f'Could not divide a {other.__class__.__name__} and a {self.__class__.__name__} '
                            f'of a different length')

    def _comparison_common(self, other, operator='__eq__'):
        if isinstance(other, DataBase):
            if not (self.name == other.name and
                    len(self) == len(other) and
                    Unit(self.units).is_compatible_with(other.units)):
                return False
            if self.dim != other.dim:
                return False
            eq = True
            for ind in range(len(self)):
                if self[ind].shape != other[ind].shape:
                    eq = False
                    break
                eq = eq and np.all(getattr(self.quantities[ind], operator)(other.quantities[ind]))
            # extra attributes are not relevant as they may contain module specific data...
            # eq = eq and (self.extra_attributes == other.extra_attributes)
            # for attribute in self.extra_attributes:
            #     eq = eq and (getattr(self, attribute) == getattr(other, attribute))
            return eq
        elif isinstance(other, numbers.Number):
            return np.all(getattr(self[0], operator)(other))
        else:
            raise TypeError()

    def __eq__(self, other):
        return self._comparison_common(other, '__eq__')

    def __le__(self, other):
        return self._comparison_common(other, '__le__')

    def __lt__(self, other):
        return self._comparison_common(other, '__lt__')

    def __ge__(self, other):
        return self._comparison_common(other, '__ge__')

    def __gt__(self, other):
        return self._comparison_common(other, '__gt__')

    def deepcopy(self):
        return copy.deepcopy(self)

    def average(self, other: 'DataBase', weight: int) -> 'DataBase':
        """ Compute the weighted average between self and other DataBase

        Parameters
        ----------
        other_data: DataBase
        weight: int
            The weight the 'other' holds with respect to self
        Returns
        -------
        DataBase: the averaged DataBase object
        """
        if isinstance(other, DataBase) and len(other) == len(self) and isinstance(weight, numbers.Number):
            return (other * weight + self) / (weight + 1)
        else:
            raise TypeError(f'Could not average a {other.__class__.__name__} or a {self.__class__.__name__} '
                            f'of a different length')

    def abs(self):
        """ Take the absolute value of itself"""
        new_data = copy.copy(self)
        new_data.data = [np.abs(dat) for dat in new_data]
        return new_data

    def angle(self):
        """ Take the phase value of itself"""
        new_data = copy.copy(self)
        new_data.data = [np.angle(dat) for dat in new_data]
        return new_data

    def real(self):
        """ Take the real part of itself"""
        new_data = copy.copy(self)
        new_data.data = [np.real(dat) for dat in new_data]
        return new_data

    def imag(self):
        """ Take the imaginary part of itself"""
        new_data = copy.copy(self)
        new_data.data = [np.imag(dat) for dat in new_data]
        return new_data

    def flipud(self):
        """Reverse the order of elements along axis 0 (up/down)"""
        new_data = copy.copy(self)
        new_data.data = [np.flipud(dat) for dat in new_data]
        return new_data

    def fliplr(self):
        """Reverse the order of elements along axis 1 (left/right)"""
        new_data = copy.copy(self)
        new_data.data = [np.fliplr(dat) for dat in new_data]
        return new_data

    def append(self, data: DataWithAxes):
        """Append data content if the underlying arrays have the same shape and compatible units"""
        for dat in data:
            if dat.shape != self.shape:
                raise DataShapeError('Cannot append those ndarrays, they don\'t have the same shape'
                                     ' as self')
        self.data += [Q_(data_array, data.units).m_as(self.units) for data_array in data.data]
        self.labels.extend(data.labels)

    def pop(self, index: int) -> DataBase:
        """ Returns a copy of self but with data taken at the specified index"""
        dwa = self.deepcopy()
        dwa.data = [dwa.data[index]]
        dwa.labels = [dwa.labels[index]]
        return dwa

    @property
    def shape(self):
        """The shape of the nd-arrays"""
        return self._shape

    def stack_as_array(self, axis=0, dtype=None) -> np.ndarray:
        """ Stack all data arrays in a single numpy array

        Parameters
        ----------
        axis: int
            The new stack axis index, default 0
        dtype: str or np.dtype
            the dtype of the stacked array

        Returns
        -------
        np.ndarray

        See Also
        --------
        :meth:`np.stack`
        """

        return np.stack(self.data, axis=axis, dtype=dtype)

    @property
    def size(self):
        """The size of the nd-arrays"""
        return self._size

    @property
    def dim(self):
        """DataDim: the enum representing the dimensionality of the stored data"""
        return self._dim

    def set_dim(self, dim: Union[DataDim, str]):
        """Addhoc modification of dim independantly of the real data shape,
        should be used with extra care"""
        self._dim = enum_checker(DataDim, dim)

    @property
    def source(self):
        """DataSource: the enum representing the source of the data"""
        return self._source

    @source.setter
    def source(self, source_type: Union[str, DataSource]):
        """DataSource: the enum representing the source of the data"""
        source_type = enum_checker(DataSource, source_type)
        self._source = source_type

    @property
    def distribution(self):
        """DataDistribution: the enum representing the distribution of the stored data"""
        return self._distribution

    @property
    def length(self):
        """The length of data. This is the length of the list containing the nd-arrays"""
        return self._length

    @property
    def labels(self):
        return self._labels

    @labels.setter
    def labels(self, labels: List['str']):
        self._check_labels(labels)

    def _check_labels(self, labels: List['str']):
        if labels is None:
            labels = []
        else:
            labels = labels[:]
        while len(labels) < self.length:
            labels.append(f'CH{len(labels):02d}')
        self._labels = labels

    def get_data_index(self, index: int = 0) -> np.ndarray:
        """Get the data by its index in the list, same as self[index]"""
        return self.data[index]

    @staticmethod
    def _check_data_type(data: List[np.ndarray]) -> List[np.ndarray]:
        """make sure data is a list of nd-arrays"""
        is_valid = True
        if data is None:
            is_valid = False
        if not isinstance(data, list):
            # try to transform the data to regular type
            if isinstance(data, np.ndarray):
                warnings.warn(DataTypeWarning(f'Your data should be a list of numpy arrays not just a single numpy'
                                              f' array, wrapping them with a list'))
                data = [data]
            elif isinstance(data, numbers.Number):
                warnings.warn(DataTypeWarning(f'Your data should be a list of numpy arrays not just a single numpy'
                                              f' array, wrapping them with a list'))
                data = [np.array([data])]
            else:
                is_valid = False
        if isinstance(data, list):
            if len(data) == 0:
                is_valid = False
            elif not isinstance(data[0], np.ndarray):
                is_valid = False
            elif len(data[0].shape) == 0:
                is_valid = False
        if not is_valid:
            raise TypeError(f'Data should be an non-empty list of non-empty numpy arrays')
        return data

    def check_shape_from_data(self, data: List[np.ndarray]):
        self._shape = data[0].shape

    @staticmethod
    def _get_dim_from_data(data: List[np.ndarray]) -> DataDim:
        shape = data[0].shape
        size = data[0].size
        if len(shape) == 1 and size == 1:
            dim = DataDim['Data0D']
        elif len(shape) == 1 and size > 1:
            dim = DataDim['Data1D']
        elif len(shape) == 2:
            dim = DataDim['Data2D']
        else:
            dim = DataDim['DataND']
        return dim

    def get_dim_from_data(self, data: List[np.ndarray]):
        """Get the dimensionality DataDim from data"""
        self.check_shape_from_data(data)
        self._size = data[0].size
        self._length = len(data)
        if len(self._shape) == 1 and self._size == 1:
            dim = DataDim['Data0D']
        elif len(self._shape) == 1 and self._size > 1:
            dim = DataDim['Data1D']
        elif len(self._shape) == 2:
            dim = DataDim['Data2D']
        else:
            dim = DataDim['DataND']
        return dim

    def _check_shape_dim_consistency(self, data: List[np.ndarray]):
        """Process the dim from data or make sure data and DataDim are coherent"""
        dim = self.get_dim_from_data(data)
        if self._dim is None:
            self._dim = dim
        else:
            self._dim = enum_checker(DataDim, self._dim)
            if self._dim != dim:
                warnings.warn(
                    DataDimWarning('The specified dimensionality is not coherent with the data '
                                   'shape, replacing it'))
                self._dim = dim

    def _check_same_shape(self, data: List[np.ndarray]):
        """Check that all nd-arrays have the same shape"""
        for dat in data:
            if dat.shape != self.shape:
                raise DataShapeError('The shape of the ndarrays in data is not the same')

    @property
    def quantities(self) -> list[Q_]:
        """ Get the arrays as pint quantities (with units)"""
        return [Q_(array, self.units) for array in self.data]

    @property
    def data(self) -> List[np.ndarray]:
        """List[np.ndarray]: get/set (and check) the data the object is storing"""
        return self._data

    @data.setter
    def data(self, data: List[np.ndarray]):
        data = self._check_data_type(data)
        self._check_shape_dim_consistency(data)
        self._check_same_shape(data)
        self._data = data

    def to_dict(self):
        """ Get the data arrays into dictionary whose keys are the labels"""
        data_dict = OrderedDict([])
        for ind in range(len(self)):
            data_dict[self.labels[ind]] = self[ind]
        return data_dict

    def to_dB(self) -> DataBase:
        """ Get a new data object in decibels

        new in 4.3.0
        """
        new_data = copy.deepcopy(self)
        for ind_array in range(len(new_data)):
            new_data[ind_array] = 10 * np.log10(self[ind_array] / self[ind_array].max())
        new_data._units = 'dB'
        return new_data


class AxesManagerBase:
    def __init__(self, data_shape: Tuple[int], axes: List[Axis], nav_indexes=None, sig_indexes=None, **kwargs):
        self._data_shape = data_shape[:]  # initial shape needed for self._check_axis
        self._axes = axes[:]
        self._nav_indexes = nav_indexes
        self._sig_indexes = sig_indexes if sig_indexes is not None else self.compute_sig_indexes()

        self._check_axis(self._axes)
        self._manage_named_axes(self._axes, **kwargs)

    @property
    def axes(self):
        return self._axes

    @axes.setter
    def axes(self, axes: List[Axis]):
        self._axes = axes[:]
        self._check_axis(self._axes)

    @abstractmethod
    def _check_axis(self, axes):
        ...

    @abstractmethod
    def get_sorted_index(self, axis_index: int = 0, spread_index=0) -> Tuple[np.ndarray, Tuple[slice]]:
        """ Get the index to sort the specified axis

        Parameters
        ----------
        axis_index: int
            The index along which one should sort the data
        spread_index: int
            for spread data only, specifies which spread axis to use

        Returns
        -------
        np.ndarray: the sorted index from the specified axis
        tuple of slice:
            used to slice the underlying data
        """
        ...

    @abstractmethod
    def get_axis_from_index_spread(self, index: int, spread_order: int) -> Axis:
        """in spread mode, different nav axes have the same index (but not
        the same spread_order integer value)

        """
        ...

    def compute_sig_indexes(self):
        _shape = list(self._data_shape)
        indexes = list(np.arange(len(self._data_shape)))
        for index in self.nav_indexes:
            if index in indexes:
                indexes.pop(indexes.index(index))
        return tuple(indexes)

    def _has_get_axis_from_index(self, index: int):
        """Check if the axis referred by a given data dimensionality index is present

        Returns
        -------
        bool: True if the axis has been found else False
        Axis or None: return the axis instance if has the axis else None
        """
        if index > len(self._data_shape) or index < 0:
            raise IndexError('The specified index does not correspond to any data dimension')
        for axis in self.axes:
            if axis.index == index:
                return True, axis
        return False, None

    def _manage_named_axes(self, axes, x_axis=None, y_axis=None, nav_x_axis=None, nav_y_axis=None):
        """This method make sur old style Data is still compatible, especially when using x_axis or y_axis parameters"""
        modified = False
        if x_axis is not None:
            modified = True
            index = 0
            if len(self._data_shape) == 1 and not self._has_get_axis_from_index(0)[0]:
                # in case of Data1D the x_axis corresponds to the first data dim
                index = 0
            elif len(self._data_shape) == 2 and not self._has_get_axis_from_index(1)[0]:
                # in case of Data2D the x_axis corresponds to the second data dim (columns)
                index = 1
            axes.append(Axis(x_axis.label, x_axis.units, x_axis.data, index=index))

        if y_axis is not None:

            if len(self._data_shape) == 2 and not self._has_get_axis_from_index(0)[0]:
                modified = True
                # in case of Data2D the y_axis corresponds to the first data dim (lines)
                axes.append(Axis(y_axis.label, y_axis.units, y_axis.data, index=0))

        if nav_x_axis is not None:
            if len(self.nav_indexes) > 0:
                modified = True
                # in case of DataND the y_axis corresponds to the first data dim (lines)
                axes.append(Axis(nav_x_axis.label, nav_x_axis.units, nav_x_axis.data, index=self._nav_indexes[0]))

        if nav_y_axis is not None:
            if len(self.nav_indexes) > 1:
                modified = True
                # in case of Data2D the y_axis corresponds to the first data dim (lines)
                axes.append(Axis(nav_y_axis.label, nav_y_axis.units, nav_y_axis.data, index=self._nav_indexes[1]))

        if modified:
            self._check_axis(axes)

    @property
    def shape(self) -> Tuple[int]:
        # self._data_shape = self.compute_shape_from_axes()
        return self._data_shape

    @abstractmethod
    def compute_shape_from_axes(self):
        ...

    @property
    def sig_shape(self) -> tuple:
        return tuple([self.shape[ind] for ind in self.sig_indexes])

    @property
    def nav_shape(self) -> tuple:
        return tuple([self.shape[ind] for ind in self.nav_indexes])

    def append_axis(self, axis: Axis):
        self._axes.append(axis)
        self._check_axis([axis])

    @property
    def nav_indexes(self) -> IterableType[int]:
        return self._nav_indexes

    @nav_indexes.setter
    def nav_indexes(self, nav_indexes: IterableType[int]):
        if isinstance(nav_indexes, Iterable):
            nav_indexes = tuple(nav_indexes)
            valid = True
            for index in nav_indexes:
                if index not in self.get_axes_index():
                    logger.warning('Could not set the corresponding nav_index into the data object, not enough'
                                   ' Axis declared')
                    valid = False
                    break
            if valid:
                self._nav_indexes = nav_indexes
        else:
            logger.warning('Could not set the corresponding sig_indexes into the data object, should be an iterable')
        self.sig_indexes = self.compute_sig_indexes()
        self.shape

    @property
    def sig_indexes(self) -> IterableType[int]:
        return self._sig_indexes

    @sig_indexes.setter
    def sig_indexes(self, sig_indexes: IterableType[int]):
        if isinstance(sig_indexes, Iterable):
            sig_indexes = tuple(sig_indexes)
            valid = True
            for index in sig_indexes:
                if index in self._nav_indexes:
                    logger.warning('Could not set the corresponding sig_index into the axis manager object, '
                                   'the axis is already affected to the navigation axis')
                    valid = False
                    break
                if index not in self.get_axes_index():
                    logger.warning('Could not set the corresponding nav_index into the data object, not enough'
                                   ' Axis declared')
                    valid = False
                    break
            if valid:
                self._sig_indexes = sig_indexes
        else:
            logger.warning('Could not set the corresponding sig_indexes into the data object, should be an iterable')

    @property
    def nav_axes(self) -> List[int]:
        deprecation_msg('nav_axes parameter should not be used anymore, use nav_indexes')
        return self._nav_indexes

    @nav_axes.setter
    def nav_axes(self, nav_indexes: List[int]):
        deprecation_msg('nav_axes parameter should not be used anymore, use nav_indexes')
        self.nav_indexes = nav_indexes

    def is_axis_signal(self, axis: Axis) -> bool:
        """Check if an axis is considered signal or navigation"""
        return axis.index in self._nav_indexes

    def is_axis_navigation(self, axis: Axis) -> bool:
        """Check if an axis  is considered signal or navigation"""
        return axis.index not in self._nav_indexes

    @abstractmethod
    def get_shape_from_index(self, index: int) -> int:
        """Get the data shape at the given index"""
        ...

    def get_axes_index(self) -> List[int]:
        """Get the index list from the axis objects"""
        return [axis.index for axis in self._axes]

    @abstractmethod
    def get_axis_from_index(self, index: int, create: bool = False) -> List[Axis]:
        ...

    def get_axis_from_index_spread(self, index: int, spread_order: int) -> Axis:
        """Only valid for Spread data"""
        ...

    def get_nav_axes(self) -> List[Axis]:
        """Get the navigation axes corresponding to the data

        Use get_axis_from_index for all index in self.nav_indexes, but in spread distribution, one index may
        correspond to multiple nav axes, see Spread data distribution


        """
        return list(mutils.flatten([copy.copy(self.get_axis_from_index(index, create=True))
                                    for index in self.nav_indexes]))

    def get_signal_axes(self):
        if self.sig_indexes is None:
            self._sig_indexes = tuple([int(axis.index) for axis in self.axes if axis.index not in self.nav_indexes])
        axes = []
        for index in self._sig_indexes:
            axes_tmp = copy.copy(self.get_axis_from_index(index, create=True))
            for ax in axes_tmp:
                if ax.size > 1:
                    axes.append(ax)
        return axes

    def is_axis_signal(self, axis: Axis) -> bool:
        """Check if an axis is considered signal or navigation"""
        return axis.index in self._nav_indexes

    def is_axis_navigation(self, axis: Axis) -> bool:
        """Check if an axis  is considered signal or navigation"""
        return axis.index not in self._nav_indexes

    def __repr__(self):
        return self._get_dimension_str()

    @abstractmethod
    def _get_dimension_str(self):
        ...


class AxesManagerUniform(AxesManagerBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def compute_shape_from_axes(self):
        if len(self.axes) != 0:
            shape = []
            for ind in range(len(self.axes)):
                shape.append(len(self.get_axis_from_index(ind, create=True)[0]))
        else:
            shape = self._data_shape
        return tuple(shape)

    def get_shape_from_index(self, index: int) -> int:
        """Get the data shape at the given index"""
        if index > len(self._data_shape) or index < 0:
            raise IndexError('The specified index does not correspond to any data dimension')
        return self._data_shape[index]

    def _check_axis(self, axes: List[Axis]):
        """Check all axis to make sure of their type and make sure their data are properly referring to the data index

        See Also
        --------
        :py:meth:`Axis.create_linear_data`
        """
        for ind, axis in enumerate(axes):
            if not isinstance(axis, Axis):
                raise TypeError(f'An axis of {self.__class__.__name__} should be an Axis object')
            if self.get_shape_from_index(axis.index) != axis.size:
                warnings.warn(DataSizeWarning('The size of the axis is not coherent with the shape of the data. '
                                              'Replacing it with a linspaced version: np.array([0, 1, 2, ...])'))
                axis.size = self.get_shape_from_index(axis.index)
                axis.scaling = 1
                axis.offset = 0
                axes[ind] = axis
        self._axes = axes

    def get_axis_from_index(self, index: int, create: bool = False) -> List[Axis]:
        """Get the axis referred by a given data dimensionality index

        If the axis is absent, create a linear one to fit the data shape if parameter create is True

        Parameters
        ----------
        index: int
            The index referring to the data ndarray shape
        create: bool
            If True and the axis referred by index has not been found in axes, create one

        Returns
        -------
        List[Axis] or None: return the list of axis instance if Data has the axis (or it has been created) else None

        See Also
        --------
        :py:meth:`Axis.create_linear_data`
        """
        index = int(index)
        has_axis, axis = self._has_get_axis_from_index(index)
        if not has_axis:
            if create:
                warnings.warn(DataIndexWarning(f'The axis requested with index {index} is not present, '
                                               f'creating a linear one...'))
                axis = Axis(index=index, offset=0, scaling=1)
                axis.size = self.get_shape_from_index(index)
            else:
                warnings.warn(DataIndexWarning(f'The axis requested with index {index} is not present, returning None'))
        return [axis]

    def get_axis_from_index_spread(self, index: int, spread_order: int) -> Axis:
        """in spread mode, different nav axes have the same index (but not
        the same spread_order integer value)

        """
        return None

    def get_sorted_index(self, axis_index: int = 0, spread_index=0) -> Tuple[np.ndarray, Tuple[slice]]:
        """ Get the index to sort the specified axis

        Parameters
        ----------
        axis_index: int
            The index along which one should sort the data
        spread_index: int
            for spread data only, specifies which spread axis to use

        Returns
        -------
        np.ndarray: the sorted index from the specified axis
        tuple of slice:
            used to slice the underlying data
        """

        axes = self.get_axis_from_index(axis_index)
        if axes[0] is not None:
            sorted_index = np.argsort(axes[0].get_data())
            axes[0].data = axes[0].get_data()[sorted_index]
            slices = []
            for ind in range(len(self.shape)):
                if ind == axis_index:
                    slices.append(sorted_index)
                else:
                    slices.append(Ellipsis)
            slices = tuple(slices)
            return sorted_index, slices
        else:
            return None, None

    def _get_dimension_str(self):
        string = "("
        for nav_index in self.nav_indexes:
            string += str(self._data_shape[nav_index]) + ", "
        string = string.rstrip(", ")
        string += "|"
        for sig_index in self.sig_indexes:
            string += str(self._data_shape[sig_index]) + ", "
        string = string.rstrip(", ")
        string += ")"
        return string


class AxesManagerSpread(AxesManagerBase):
    """For this particular data category, some explanation is needed, see example below:

    Examples
    --------
    One take images data (20x30) as a function of 2 parameters, say xaxis and yaxis non-linearly spaced on a regular
    grid.

    data.shape = (150, 20, 30)
    data.nav_indexes = (0,)

    The first dimension (150) corresponds to the navigation (there are 150 non uniform data points taken)
    The  second and third could correspond to signal data, here an image of size (20x30)
    so:
    * nav_indexes is (0, )
    * sig_indexes are (1, 2)

    xaxis = Axis(name=xaxis, index=0, data...) length 150
    yaxis = Axis(name=yaxis, index=0, data...) length 150

    In fact from such a data shape the number of navigation axes in unknown . In our example, they are 2. To somehow
    keep track of some ordering in these navigation axes, one adds an attribute to the Axis object: the spread_order 
    xaxis = Axis(name=xaxis, index=0, spread_order=0, data...) length 150
    yaxis = Axis(name=yaxis, index=0, spread_order=1, data...) length 150
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _check_axis(self, axes: List[Axis]):
        """Check all axis to make sure of their type and make sure their data are properly referring to the data index

        """
        for axis in axes:
            if not isinstance(axis, Axis):
                raise TypeError(f'An axis of {self.__class__.__name__} should be an Axis object')
            elif len(self.nav_indexes) != 1:
                raise ValueError('Spread data should have only one specified index in self.nav_indexes')
            elif axis.index in self.nav_indexes:
                if axis.size != 1 and (axis.size != self._data_shape[self.nav_indexes[0]]):
                    raise DataLengthError('all navigation axes should have the same size')

    def compute_shape_from_axes(self):
        """Get data shape from axes

        First get the nav length from one of the navigation axes
        Then check for signal axes
        """
        if len(self.axes) != 0:

            axes = sorted(self.axes, key=lambda axis: axis.index)

            shape = []
            for axis in axes:
                if axis.index in self.nav_indexes:
                    shape.append(axis.size)
                    break
            for axis in axes:
                if axis.index not in self.nav_indexes:
                    shape.append(axis.size)
        else:
            shape = self._data_shape
        return tuple(shape)

    def get_shape_from_index(self, index: int) -> int:
        """Get the data shape at the given index"""
        if index > len(self._data_shape) or index < 0:
            raise IndexError('The specified index does not correspond to any data dimension')
        return self._data_shape[index]

    def get_axis_from_index(self, index: int, create: bool = False) -> List[Axis]:
        """in spread mode, different nav axes have the same index (but not
        the same spread_order integer value) so may return multiple axis

        No possible "linear" creation in this mode except if the index is a signal index

        """
        if index in self.nav_indexes:
            axes = []
            for axis in self.axes:
                if axis.index == index:
                    axes.append(axis)
            return axes
        else:
            index = int(index)
            try:
                has_axis, axis = self._has_get_axis_from_index(index)
            except IndexError:
                axis = [None]
                has_axis = False
                return axis

            if not has_axis and index in self.sig_indexes:
                if create:
                    warnings.warn(DataIndexWarning(f'The axis requested with index {index} is not present, '
                                                   f'creating a linear one...'))
                    axis = Axis(index=index, offset=0, scaling=1)
                    axis.size = self.get_shape_from_index(index)
                else:
                    warnings.warn(DataIndexWarning(f'The axis requested with index {index} is not present, returning None'))

            return [axis]

    def get_axis_from_index_spread(self, index: int, spread_order: int) -> Axis:
        """in spread mode, different nav axes have the same index (but not
        the same spread_order integer value)

        """
        for axis in self.axes:
            if axis.index == index and axis.spread_order == spread_order:
                return axis

    def get_sorted_index(self, axis_index: int = 0, spread_index=0) -> Tuple[np.ndarray, Tuple[slice]]:
        """ Get the index to sort the specified axis

        Parameters
        ----------
        axis_index: int
            The index along which one should sort the data
        spread_index: int
            for spread data only, specifies which spread axis to use

        Returns
        -------
        np.ndarray: the sorted index from the specified axis
        tuple of slice:
            used to slice the underlying data
        """

        if axis_index in self.nav_indexes:
            axis = self.get_axis_from_index_spread(axis_index, spread_index)
        else:
            axis = self.get_axis_from_index(axis_index)[0]

        if axis is not None:
            sorted_index = np.argsort(axis.get_data())
            slices = []
            for ind in range(len(self.shape)):
                if ind == axis_index:
                    slices.append(sorted_index)
                else:
                    if slices[-1] is Ellipsis:  # only one ellipsis
                        slices.append(Ellipsis)
            slices = tuple(slices)

            for nav_index in self.nav_indexes:
                for axis in self.get_axis_from_index(nav_index):
                    axis.data = axis.get_data()[sorted_index]

            return sorted_index, slices
        else:
            return None, None

    def get_axis_from_index_spread(self, index: int, spread_order: int) -> Axis:
        for axis in self.axes:
            if axis.index == index and axis.spread_order == spread_order:
                return axis

    def _get_dimension_str(self):
        try:
            string = "("
            for nav_index in self.nav_indexes:
                string += str(self._data_shape[nav_index]) + ", "
                break
            string = string.rstrip(", ")
            string += "|"
            for sig_index in self.sig_indexes:
                string += str(self._data_shape[sig_index]) + ", "
            string = string.rstrip(", ")
            string += ")"
        except Exception as e:
            string = f'({self._data_shape})'
        finally:
            return string


class DataWithAxes(DataBase):
    """Data object with Axis objects corresponding to underlying data nd-arrays

    Parameters
    ----------
    axes: list of Axis
        the list of Axis object for proper plotting, calibration ...
    nav_indexes: tuple of int
        highlight which Axis in axes is Signal or Navigation axis depending on the content:
        For instance, nav_indexes = (2,), means that the axis with index 2 in a at least 3D ndarray data is the first
        navigation axis
        For instance, nav_indexes = (3,2), means that the axis with index 3 in a at least 4D ndarray data is the first
        navigation axis while the axis with index 2 is the second navigation Axis. Axes with index 0 and 1 are signal
        axes of 2D ndarray data
    errors: list of ndarray.
        The list should match the length of the data attribute while the ndarrays
        should match the data ndarray
    """

    def __init__(self, *args, axes: List[Axis] = [],
                 nav_indexes: Tuple[int] = (),
                 errors: Iterable[np.ndarray] = None,
                 **kwargs):

        if 'nav_axes' in kwargs:
            deprecation_msg('nav_axes parameter should not be used anymore, use nav_indexes')
            nav_indexes = kwargs.pop('nav_axes')

        x_axis = kwargs.pop('x_axis') if 'x_axis' in kwargs else None
        y_axis = kwargs.pop('y_axis') if 'y_axis' in kwargs else None

        nav_x_axis = kwargs.pop('nav_x_axis') if 'nav_x_axis' in kwargs else None
        nav_y_axis = kwargs.pop('nav_y_axis') if 'nav_y_axis' in kwargs else None

        super().__init__(*args, **kwargs)

        self._axes = axes

        other_kwargs = dict(x_axis=x_axis, y_axis=y_axis, nav_x_axis=nav_x_axis, nav_y_axis=nav_y_axis)

        self.set_axes_manager(self.shape, axes=axes, nav_indexes=nav_indexes, **other_kwargs)

        self.inav: Iterable[DataWithAxes] = SpecialSlicersData(self, True)
        self.isig: Iterable[DataWithAxes] = SpecialSlicersData(self, False)

        self.get_dim_from_data_axes()  # in DataBase, dim is processed from the shape of data, but if axes are provided
        #then use get_dim_from axes
        self._check_errors(errors)

    def _check_errors(self, errors: Iterable[np.ndarray]):
        """ Make sure the errors object is adapted to the len/shape of the dwa object

        new in 4.2.0
        """
        check = False
        if errors is None:
            self._errors = None
            return
        if isinstance(errors, (tuple, list)) and len(errors) == len(self):
            if np.all([isinstance(error, np.ndarray) for error in errors]):
                if np.all([error_array.shape == self.shape for error_array in errors]):
                    check = True
                else:
                    logger.warning(f'All error objects should have the same shape as the data'
                                   f'objects')
            else:
                logger.warning(f'All error objects should be np.ndarray')

        if not check:
            logger.warning('the errors field is incompatible with the structure of the data')
            self._errors = None
        else:
            self._errors = errors

    @property
    def errors(self):
        """ Get/Set the errors bar values as a list of np.ndarray

        new in 4.2.0
        """
        return self._errors

    @errors.setter
    def errors(self, errors: Iterable[np.ndarray]):
        self._check_errors(errors)

    def get_error(self, index):
        """ Get a particular error ndarray at the given index in the list

        new in 4.2.0
        """
        if self._errors is not None:  #because to the initial check we know it is a list of ndarrays
            return self._errors[index]
        else:
            return np.array([0])  # this could be added to any numpy array of any shape

    def errors_as_dwa(self):
        """ Get a dwa from self replacing the data content with the error attribute (if not None)

        New in 4.2.0
        """
        if self.errors is not None:
            dwa = self.deepcopy_with_new_data(self.errors)
            dwa.name = f'{self.name}_errors'
            dwa.errors = None
            return dwa
        else:
            raise ValueError(f'Cannot create a dwa from a None, should be a list of ndarray')

    def plot(self, plotter_backend: str = config('plotting', 'backend'), *args, viewer=None,
             **kwargs):
        """ Call a plotter factory and its plot method over the actual data"""
        return plotter_factory.get(plotter_backend).plot(self, *args, viewer=viewer, **kwargs)

    def set_axes_manager(self, data_shape, axes, nav_indexes, **kwargs):
        if self.distribution.name == 'uniform' or len(nav_indexes) == 0:
            self._distribution = DataDistribution['uniform']
            self.axes_manager = AxesManagerUniform(data_shape=data_shape, axes=axes,
                                                   nav_indexes=nav_indexes,
                                                   **kwargs)
        elif self.distribution.name == 'spread':
            self.axes_manager = AxesManagerSpread(data_shape=data_shape, axes=axes,
                                                  nav_indexes=nav_indexes,
                                                  **kwargs)
        else:
            raise ValueError(f'Such a data distribution ({data.distribution}) has no AxesManager')

    def __eq__(self, other):
        is_equal = super().__eq__(other)
        if not is_equal:
            return is_equal
        if isinstance(other, DataWithAxes):
            for ind in list(self.nav_indexes) + list(self.sig_indexes):
                axes_self = self.get_axis_from_index(ind)
                axes_other = other.get_axis_from_index(ind)
                if len(axes_other) != len(axes_self):
                    return False
                for ind_ax in range(len(axes_self)):
                    if axes_self[ind_ax] != axes_other[ind_ax]:
                        return False
            if self.errors is None:
                is_equal = is_equal and other.errors is None
            else:
                for ind_error in range(len(self.errors)):
                    if not np.allclose(self.errors[ind_error], other.errors[ind_error]):
                        return False
        return is_equal

    def __repr__(self):
        return (f'<{self.__class__.__name__}: {self.name} '
                f'<u: {self.units}> '
                f'<len:{self.length}> {self._am}>')

    def sort_data(self, axis_index: int = 0, spread_index=0, inplace=False) -> DataWithAxes:
        """ Sort data along a given axis, default is 0

        Parameters
        ----------
        axis_index: int
            The index along which one should sort the data
        spread_index: int
            for spread data only, specifies which spread axis to use
        inplace: bool
            modify in place or not the data (and its axes)

        Returns
        -------
        DataWithAxes
        """
        if inplace:
            data = self
        else:
            data = self.deepcopy()
        sorted_index, slices = data._am.get_sorted_index(axis_index, spread_index)
        if sorted_index is not None:
            for ind in range(len(data)):
                data.data[ind] = data.data[ind][slices]
        return data

    def transpose(self):
        """replace the data by their transposed version

        Valid only for 2D data
        """
        if self.dim == 'Data2D':
            self.data[:] = [data.T for data in self.data]
            for axis in self.axes:
                axis.index = 0 if axis.index == 1 else 1

    def crop_at_along(self, coordinates_tuple: Tuple):
        slices = []
        for coordinates in coordinates_tuple:
            axis = self.get_axis_from_index(0)[0]
            indexes = axis.find_indexes(coordinates)
            slices.append(slice(indexes))

        return self._slicer(slices, False)

    def mean(self, axis: int = 0) -> DataWithAxes:
        """Process the mean of the data on the specified axis and returns the new data

        Parameters
        ----------
        axis: int

        Returns
        -------
        DataWithAxes
        """
        dat_mean = []
        for dat in self.data:
            mean = np.mean(dat, axis=axis)
            if isinstance(mean, numbers.Number):
                mean = np.array([mean])
            dat_mean.append(mean)
        return self.deepcopy_with_new_data(dat_mean, remove_axes_index=axis)
    
    def sum(self, axis: int = 0) -> DataWithAxes:
        """Process the sum of the data on the specified axis and returns the new data

        Parameters
        ----------
        axis: int

        Returns
        -------
        DataWithAxes
        """
        dat_sum = []
        for dat in self.data:
            dat_sum.append(np.sum(dat, axis=axis))
        return self.deepcopy_with_new_data(dat_sum, remove_axes_index=axis)

    def interp(self,  new_axis_data: Union[Axis, np.ndarray], **kwargs) -> DataWithAxes:
        """Performs linear interpolation for 1D data only.
        
        For more complex ones, see :py:meth:`scipy.interpolate`

        Parameters
        ----------
        new_axis_data: Union[Axis, np.ndarray]
            The coordinates over which to do the interpolation
        kwargs: dict
            extra named parameters to be passed to the :py:meth:`~numpy.interp` method

        Returns
        -------
        DataWithAxes

        See Also
        --------
        :py:meth:`~numpy.interp`
        :py:meth:`~scipy.interpolate`
        """
        if self.dim != DataDim['Data1D']:
            raise ValueError('For basic interpolation, only 1D data are supported')

        data_interpolated = []
        axis_obj = self.get_axis_from_index(0)[0]
        if isinstance(new_axis_data, np.ndarray):
            new_axis_data = Axis(axis_obj.label, axis_obj.units, data=new_axis_data)

        for dat in self.data:
            data_interpolated.append(np.interp(new_axis_data.get_data(), axis_obj.get_data(), dat,
                                               **kwargs))
        new_data = DataCalculated(f'{self.name}_interp', data=data_interpolated,
                                  axes=[new_axis_data],
                                  labels=self.labels)
        return new_data

    def ft(self, axis: int = 0) -> DataWithAxes:
        """Process the Fourier Transform of the data on the specified axis and returns the new data

        Parameters
        ----------
        axis: int

        Returns
        -------
        DataWithAxes

        See Also
        --------
        :py:meth:`~pymodaq.utils.math_utils.ft`, :py:meth:`~numpy.fft.fft`
        """
        dat_ft = []
        axis_obj = self.get_axis_from_index(axis)[0].copy()
        omega_grid, time_grid = mutils.ftAxis_time(len(axis_obj),
                                                   np.abs(axis_obj.max() - axis_obj.min()))
        for dat in self.data:
            dat_ft.append(mutils.ft(dat, dim=axis))
        new_data = self.deepcopy_with_new_data(dat_ft)
        axis_obj = new_data.get_axis_from_index(axis)[0]
        axis_obj.data = omega_grid
        axis_obj.label = f'ft({axis_obj.label})'
        axis_obj.units = f'rad/{axis_obj.units}'
        return new_data

    def ift(self, axis: int = 0) -> DataWithAxes:
        """Process the inverse Fourier Transform of the data on the specified axis and returns the
        new data

        Parameters
        ----------
        axis: int

        Returns
        -------
        DataWithAxes

        See Also
        --------
        :py:meth:`~pymodaq.utils.math_utils.ift`, :py:meth:`~numpy.fft.ifft`
        """
        dat_ift = []
        axis_obj = self.get_axis_from_index(axis)[0].copy()
        omega_grid, time_grid = mutils.ftAxis_time(len(axis_obj),
                                                   np.abs(axis_obj.max() - axis_obj.min()))
        for dat in self.data:
            dat_ift.append(mutils.ift(dat, dim=axis))
        new_data = self.deepcopy_with_new_data(dat_ift)
        axis_obj = new_data.get_axis_from_index(axis)[0]
        axis_obj.data = omega_grid
        axis_obj.label = f'ift({axis_obj.label})'
        axis_obj.units = str(Unit(f'rad/({axis_obj.units})'))
        return new_data

    def fit(self, function: Callable, initial_guess: IterableType, data_index: int = None,
            axis_index: int = 0, **kwargs) -> DataCalculated:
        """ Apply 1D curve fitting using the scipy optimization package

        Parameters
        ----------
        function: Callable
            a callable to be used for the fit
        initial_guess: Iterable
            The initial parameters for the fit
        data_index: int
            The index of the data over which to do the fit, if None apply the fit to all
        axis_index: int
            the axis index to use for the fit (if multiple) but there should be only one
        kwargs: dict
            extra named parameters applied to the curve_fit scipy method

        Returns
        -------
        DataCalculated containing the evaluation of the fit on the specified axis

        See Also
        --------
        :py:meth:`~scipy.optimize.curve_fit`
        """
        import scipy.optimize as opt
        if self.dim != DataDim['Data1D']:
            raise ValueError('Integrated fitting only works for 1D data')
        axis = self.get_axis_from_index(axis_index)[0].copy()
        axis_array = axis.get_data()
        if data_index is None:
            datalist_to_fit = self.data
            labels = [f'{label}_fit' for label in self.labels]
        else:
            datalist_to_fit = [self.data[data_index]]
            labels = [f'{self.labels[data_index]}_fit']

        datalist_fitted = []
        fit_coeffs = []
        for data_array in datalist_to_fit:
            popt, pcov = opt.curve_fit(function, axis_array, data_array, p0=initial_guess, **kwargs)
            datalist_fitted.append(function(axis_array, *popt))
            fit_coeffs.append(popt)

        return DataCalculated(f'{self.name}_fit', data=datalist_fitted,
                              labels=labels,
                              axes=[axis], fit_coeffs=fit_coeffs)

    def find_peaks(self, height=None, threshold=None, **kwargs) -> DataToExport:
        """ Apply the scipy find_peaks method to 1D data

        Parameters
        ----------
        height: number or ndarray or sequence, optional
        threshold: number or ndarray or sequence, optional
        kwargs: dict
            extra named parameters applied to the find_peaks scipy method

        Returns
        -------
        DataCalculated

        See Also
        --------
        :py:meth:`~scipy.optimize.find_peaks`
        """
        if self.dim != DataDim['Data1D']:
            raise ValueError('Finding peaks only works for 1D data')
        from scipy.signal import find_peaks
        peaks_indices = []
        dte = DataToExport('peaks')
        for ind in range(len(self)):
            peaks, properties = find_peaks(self[ind], height, threshold, **kwargs)
            peaks_indices.append(peaks)

            dte.append(DataCalculated(f'{self.labels[ind]}',
                                      data=[self[ind][peaks_indices[-1]],
                                            peaks_indices[-1]
                                            ],
                                      labels=['peak value', 'peak indexes'],
                                      axes=[Axis('peak position', self.axes[0].units,
                                                 data=self.axes[0].get_data_at(peaks_indices[-1]))])
                       )
        return dte

    def get_dim_from_data_axes(self) -> DataDim:
        """Get the dimensionality DataDim from data taking into account nav indexes
        """
        if len(self.axes) != len(self.shape):
            self._dim = self.get_dim_from_data(self.data)
        else:
            if len(self.nav_indexes) > 0:
                self._dim = DataDim['DataND']
            else:
                if len(self.axes) == 0:
                    self._dim = DataDim['Data0D']
                elif len(self.axes) == 1:
                    self._dim = DataDim['Data1D']
                elif len(self.axes) == 2:
                    self._dim = DataDim['Data2D']
        if len(self.nav_indexes) > 0:
            self._dim = DataDim['DataND']
        return self._dim

    @property
    def n_axes(self):
        """Get the number of axes (even if not specified)"""
        return len(self.axes)

    @property
    def axes(self):
        """convenience property to fetch attribute from axis_manager"""
        return self._am.axes

    @axes.setter
    def axes(self, axes: List[Axis]):
        """convenience property to set attribute from axis_manager"""
        self.set_axes_manager(self.shape, axes=axes, nav_indexes=self.nav_indexes)

    def axes_limits(self, axes_indexes: List[int] = None) -> List[Tuple[float, float]]:
        """Get the limits of specified axes (all if axes_indexes is None)"""
        if axes_indexes is None:
            return [(axis.min(), axis.max()) for axis in self.axes]
        else:
            return [(axis.min(), axis.max()) for axis in self.axes if axis.index in axes_indexes]

    @property
    def sig_indexes(self):
        """convenience property to fetch attribute from axis_manager"""
        return self._am.sig_indexes

    @property
    def nav_indexes(self):
        """convenience property to fetch attribute from axis_manager"""
        return self._am.nav_indexes

    @nav_indexes.setter
    def nav_indexes(self, indexes: List[int]):
        """create new axis manager with new navigation indexes"""
        self.set_axes_manager(self.shape, axes=self.axes, nav_indexes=indexes)
        self.get_dim_from_data_axes()

    def get_nav_axes(self) -> List[Axis]:
        return self._am.get_nav_axes()

    def get_sig_index(self) -> List[Axis]:
        return self._am.get_signal_axes()

    def get_nav_axes_with_data(self) -> List[Axis]:
        """Get the data's navigation axes making sure there is data in the data field"""
        axes = self.get_nav_axes()
        for axis in axes:
            if axis.get_data() is None:
                axis.create_linear_data(self.shape[axis.index])
        return axes

    def get_axis_indexes(self) -> List[int]:
        """Get all present different axis indexes"""
        return sorted(list(set([axis.index for axis in self.axes])))

    def get_axis_from_index(self, index, create=False):
        return self._am.get_axis_from_index(index, create)

    def get_axis_from_index_spread(self, index: int, spread: int):
        return self._am.get_axis_from_index_spread(index, spread)

    def get_axis_from_label(self, label: str) -> Axis:
        """Get the axis referred by a given label

        Parameters
        ----------
        label: str
            The label of the axis

        Returns
        -------
        Axis or None: return the axis instance if it has the right label else None
        """
        for axis in self.axes:
            if axis.label == label:
                return axis

    def create_missing_axes(self):
        """Check if given the data shape, some axes are missing to properly define the data
        (especially for plotting)"""
        axes = self.axes[:]
        for index in self.nav_indexes + self.sig_indexes:
            if (len(self.get_axis_from_index(index)) != 0 and
                    self.get_axis_from_index(index)[0] is None):
                axes_tmp = self.get_axis_from_index(index, create=True)
                for ax in axes_tmp:
                    if ax.size > 1:
                        axes.append(ax)
        self.axes = axes

    def _compute_slices(self, slices, is_navigation=True):
        """Compute the total slice to apply to the data

        Filling in Ellipsis when no slicing should be done
        """
        if isinstance(slices, numbers.Number) or isinstance(slices, slice):
            slices = [slices]
        if is_navigation:
            indexes = self._am.nav_indexes
        else:
            indexes = self._am.sig_indexes
        total_slices = []
        slices = list(slices)
        for ind in range(len(self.shape)):
            if ind in indexes:
                total_slices.append(slices.pop(0))
            elif len(total_slices) == 0:
                total_slices.append(Ellipsis)
            elif not (Ellipsis in total_slices and total_slices[-1] is Ellipsis):
                total_slices.append(slice(None))
        total_slices = tuple(total_slices)
        return total_slices

    def check_squeeze(self, total_slices: List[slice], is_navigation: bool):

        do_squeeze = True
        if 1 in self.data[0][total_slices].shape:
            if not is_navigation and self.data[0][total_slices].shape.index(1) in self.nav_indexes:
                do_squeeze = False
            elif is_navigation and self.data[0][total_slices].shape.index(1) in self.sig_indexes:
                do_squeeze = False
        return do_squeeze

    def _slicer(self, slices, is_navigation=True):
        """Apply a given slice to the data either navigation or signal dimension

        Parameters
        ----------
        slices: tuple of slice or int
            the slices to apply to the data
        is_navigation: bool
            if True apply the slices to the navigation dimension else to the signal ones

        Returns
        -------
        DataWithAxes
            Object of the same type as the initial data, derived from DataWithAxes. But with lower
            data size due to the slicing and with eventually less axes.
        """

        if isinstance(slices, numbers.Number) or isinstance(slices, slice):
            slices = [slices]
        total_slices = self._compute_slices(slices, is_navigation)

        do_squeeze = self.check_squeeze(total_slices, is_navigation)
        new_arrays_data = [squeeze(dat[total_slices], do_squeeze) for dat in self.data]
        tmp_axes = self._am.get_signal_axes() if is_navigation else self._am.get_nav_axes()
        axes_to_append = [copy.deepcopy(axis) for axis in tmp_axes]

        # axes_to_append are the axes to append to the new produced data
        # (basically the ones to keep)

        indexes_to_get = self.nav_indexes if is_navigation else self.sig_indexes
        # indexes_to_get are the indexes of the axes where the slice should be applied

        _indexes = list(self.nav_indexes)
        _indexes.extend(self.sig_indexes)
        lower_indexes = dict(zip(_indexes, [0 for _ in range(len(_indexes))]))
        # lower_indexes will store for each *axis index* how much the index should be reduced
        # because one axis has
        # been removed

        axes = []
        nav_indexes = [] if is_navigation else list(self._am.nav_indexes)
        for ind_slice, _slice in enumerate(slices):
            if ind_slice < len(indexes_to_get):
                ax = self._am.get_axis_from_index(indexes_to_get[ind_slice])
                if len(ax) != 0 and ax[0] is not None:
                    for ind in range(len(ax)):
                        ax[ind] = ax[ind].iaxis[_slice]

                    if not(ax[0] is None or ax[0].size <= 1):  # means the slice kept part of the axis
                        if is_navigation:
                            nav_indexes.append(self._am.nav_indexes[ind_slice])
                        axes.extend(ax)
                    else:
                        for axis in axes_to_append:  # means we removed one of the axes (and data dim),
                            # hence axis index above current index should be lowered by 1
                            if axis.index > indexes_to_get[ind_slice]:
                                lower_indexes[axis.index] += 1
                        for index in indexes_to_get[ind_slice+1:]:
                            lower_indexes[index] += 1

        axes.extend(axes_to_append)
        for axis in axes:
            axis.index -= lower_indexes[axis.index]
        for ind in range(len(nav_indexes)):
            nav_indexes[ind] -= lower_indexes[nav_indexes[ind]]

        if len(nav_indexes) != 0:
            distribution = self.distribution
        else:
            distribution = DataDistribution['uniform']

        data = DataWithAxes(self.name, data=new_arrays_data, nav_indexes=tuple(nav_indexes),
                            axes=axes,
                            source='calculated', origin=self.origin,
                            labels=self.labels[:],
                            distribution=distribution)
        return data

    def deepcopy_with_new_data(self, data: List[np.ndarray] = None,
                               remove_axes_index: Union[int, List[int]] = None,
                               source: DataSource = 'calculated',
                               keep_dim=False) -> DataWithAxes:
        """deepcopy without copying the initial data (saving memory)

        The new data, may have some axes stripped as specified in remove_axes_index

        Parameters
        ----------
        data: list of numpy ndarray
            The new data
        remove_axes_index: tuple of int
            indexes of the axis to be removed
        source: DataSource
        keep_dim: bool
            if False (the default) will calculate the new dim based on the data shape
            else keep the same (be aware it could lead to issues)

        Returns
        -------
        DataWithAxes
        """
        try:
            old_data = self.data
            self._data = None
            new_data = self.deepcopy()
            new_data._data = data
            new_data.get_dim_from_data(data)

            if source is not None:
                source = enum_checker(DataSource, source)
                new_data._source = source

            if remove_axes_index is not None:
                if not isinstance(remove_axes_index, Iterable):
                    remove_axes_index = [remove_axes_index]
                    
                lower_indexes = dict(zip(new_data.get_axis_indexes(),
                                         [0 for _ in range(len(new_data.get_axis_indexes()))]))
                # lower_indexes will store for each *axis index* how much the index should be reduced because one axis has
                # been removed

                nav_indexes = list(new_data.nav_indexes)
                sig_indexes = list(new_data.sig_indexes)
                for index in remove_axes_index:
                    for axis in new_data.get_axis_from_index(index):
                        if axis is not None:
                            new_data.axes.remove(axis)

                    if index in new_data.nav_indexes:
                        nav_indexes.pop(nav_indexes.index(index))
                    if index in new_data.sig_indexes:
                        sig_indexes.pop(sig_indexes.index(index))

                    # for ind, nav_ind in enumerate(nav_indexes):
                    #     if nav_ind > index and nav_ind not in remove_axes_index:
                    #         nav_indexes[ind] -= 1

                    # for ind, sig_ind in enumerate(sig_indexes):
                    #     if sig_ind > index:
                    #         sig_indexes[ind] -= 1
                    for axis in new_data.axes:
                        if axis.index > index and axis.index not in remove_axes_index:
                            lower_indexes[axis.index] += 1

                for axis in new_data.axes:
                    axis.index -= lower_indexes[axis.index]
                for ind in range(len(nav_indexes)):
                    nav_indexes[ind] -= lower_indexes[nav_indexes[ind]]

                new_data.nav_indexes = tuple(nav_indexes)
                # new_data._am.sig_indexes = tuple(sig_indexes)

            new_data._shape = data[0].shape
            if not keep_dim:
                new_data._dim = self._get_dim_from_data(data)
            return new_data

        except Exception as e:
            pass
        finally:
            self._data = old_data

    @property
    def _am(self) -> AxesManagerBase:
        return self.axes_manager

    def get_data_dimension(self) -> str:
        return str(self._am)

    def get_data_as_dwa(self, index: int = 0) -> DataWithAxes:
        """ Get the underlying data selected from the list at index, returned as a DataWithAxes"""
        return self.deepcopy_with_new_data([self[index]])


class DataRaw(DataWithAxes):
    """Specialized DataWithAxes set with source as 'raw'. To be used for raw data"""
    def __init__(self, *args,  **kwargs):
        if 'source' in kwargs:
            kwargs.pop('source')
        super().__init__(*args, source=DataSource['raw'], **kwargs)


class DataActuator(DataRaw):
    """Specialized DataWithAxes set with source as 'raw'.
    To be used for raw data generated by actuator plugins"""
    def __init__(self, *args, **kwargs):
        if len(args) == 0 and 'name' not in kwargs:
            args = ['actuator']
        if 'data' not in kwargs:
            kwargs['data'] = [np.array([0.])]
        elif isinstance(kwargs['data'], numbers.Number):  # useful formatting
            kwargs['data'] = [np.array([kwargs['data']])]
        super().__init__(*args, **kwargs)

    def __repr__(self):
        if self.dim.name == 'Data0D':
            return f'<{self.__class__.__name__} ({self.data[0][0]} {self.units})>'
        else:
            return f'<{self.__class__.__name__} ({self.shape} {self.units})>'

    def value(self, units: str = None) -> float:
        """Returns the underlying float value (of the first elt in the data list) if this data
        holds only a float otherwise returns a mean of the underlying data

        Parameters
        ----------

        units: str
            if unit is compatible with self.units, convert the data to these new units before
            getting the value


        """
        if self.length == 1 and self.size == 1:
            if units is not None:
                data = Q_(float(self.data[0][0]), self.units)
                return data.m_as(units)
            else:
                return float(self.data[0][0])
        else:
            if units is not None:
                data = Q_(float(np.mean(self.data[0])), self.units)
                return data.m_as(units)
            else:
                return float(np.mean(self.data[0]))

    def values(self, units: str = None) -> List[float]:
        """Returns the underlying float value (for each data array in the data list) if this data
        holds only a float otherwise returns a mean of the underlying data"""
        if self.length == 1 and self.size == 1:
            if units is not None:
                return [float(Q_(data_array[0], self.units).m_as(units))
                        for data_array in self.data]
            else:
                return [float(data_array[0])
                        for data_array in self.data]
        else:
            if units is not None:
                return [float(Q_(np.mean(data_array), self.units).m_as(units))
                        for data_array in self.data]
            else:
                return [float(np.mean(data_array)) for data_array in self.data]


class DataFromPlugins(DataRaw):
    """Specialized DataWithAxes set with source as 'raw'. To be used for raw data generated by Detector plugins

    It introduces by default to extra attributes, do_plot and do_save. Their presence can be checked in the
    extra_attributes list.

    Parameters
    ----------
    do_plot: bool
        If True the underlying data will be plotted in the DAQViewer
    do_save: bool
        If True the underlying data will be saved

    Attributes
    ----------
    do_plot: bool
        If True the underlying data will be plotted in the DAQViewer
    do_save: bool
        If True the underlying data will be saved
    """
    def __init__(self, *args, **kwargs):

        ##### for backcompatibility
        if 'plot' in kwargs:
            deprecation_msg("'plot' should not be used anymore as extra_attribute, "
                            "please use 'do_plot'")
            do_plot = kwargs.pop('plot')
            kwargs['do_plot'] = do_plot

        if 'save' in kwargs:
            deprecation_msg("'save' should not be used anymore as extra_attribute, "
                            "please use 'do_save'")
            do_save = kwargs.pop('save')
            kwargs['do_save'] = do_save
        #######

        if 'do_plot' not in kwargs:
            kwargs['do_plot'] = True
        if 'do_save' not in kwargs:
            kwargs['do_save'] = True
        super().__init__(*args, **kwargs)


class DataCalculated(DataWithAxes):
    """Specialized DataWithAxes set with source as 'calculated'. To be used for processed/calculated data"""
    def __init__(self, *args, axes=[],  **kwargs):
        if 'source' in kwargs:
            kwargs.pop('source')
        super().__init__(*args, source=DataSource['calculated'], axes=axes, **kwargs)


class DataFromRoi(DataCalculated):
    """Specialized DataWithAxes set with source as 'calculated'.To be used for processed data from region of interest"""
    def __init__(self, *args, axes=[], **kwargs):
        super().__init__(*args, axes=axes, **kwargs)


class DataToExport(DataLowLevel):
    """Object to store all raw and calculated DataWithAxes data for later exporting, saving, sending signal...

    Includes methods to retrieve data from dim, source...
    Stored data have a unique identifier their name. If some data is appended with an existing name, it will replace
    the existing data. So if you want to append data that has the same name

    Parameters
    ----------
    name: str
        The identifier of the exporting object
    data: list of DataWithAxes
        All the raw and calculated data to be exported

    Attributes
    ----------
    name
    timestamp
    data
    """

    def __init__(self, name: str, data: List[DataWithAxes] = [], **kwargs):
        """

        Parameters
        ----------
        name
        data
        """
        super().__init__(name)
        if not isinstance(data, list):
            raise TypeError('Data stored in a DataToExport object should be as a list of objects'
                            ' inherited from DataWithAxis')
        self._data = []

        self.data = data
        for key in kwargs:
            setattr(self, key, kwargs[key])

    def plot(self, plotter_backend: str = config('plotting', 'backend'), *args, **kwargs):
        """ Call a plotter factory and its plot method over the actual data"""
        return plotter_factory.get(plotter_backend).plot(self, *args, **kwargs)

    def affect_name_to_origin_if_none(self):
        """Affect self.name to all DataWithAxes children's attribute origin if this origin is not defined"""
        for dat in self.data:
            if dat.origin is None or dat.origin == '':
                dat.origin = self.name

    def __sub__(self, other: object):
        if isinstance(other, DataToExport) and len(other) == len(self):
            new_data = copy.deepcopy(self)
            for ind_dfp in range(len(self)):
                new_data[ind_dfp] = self[ind_dfp] - other[ind_dfp]
            return new_data
        else:
            raise TypeError(f'Could not substract a {other.__class__.__name__} or a {self.__class__.__name__} '
                            f'of a different length')

    def __add__(self, other: object):
        if isinstance(other, DataToExport) and len(other) == len(self):
            new_data = copy.deepcopy(self)
            for ind_dfp in range(len(self)):
                new_data[ind_dfp] = self[ind_dfp] + other[ind_dfp]
            return new_data
        else:
            raise TypeError(f'Could not add a {other.__class__.__name__} or a {self.__class__.__name__} '
                            f'of a different length')

    def __mul__(self, other: object):
        if isinstance(other, numbers.Number):
            new_data = copy.deepcopy(self)
            for ind_dfp in range(len(self)):
                new_data[ind_dfp] = self[ind_dfp] * other
            return new_data
        else:
            raise TypeError(f'Could not multiply a {other.__class__.__name__} with a {self.__class__.__name__} '
                            f'of a different length')

    def __truediv__(self, other: object):
        if isinstance(other, numbers.Number):
            return self * (1 / other)
        else:
            raise TypeError(f'Could not divide a {other.__class__.__name__} with a {self.__class__.__name__} '
                            f'of a different length')

    def average(self, other: DataToExport, weight: int) -> DataToExport:
        """ Compute the weighted average between self and other DataToExport and attributes it to self

        Parameters
        ----------
        other: DataToExport
        weight: int
            The weight the 'other_data' holds with respect to self

        """
        if isinstance(other, DataToExport) and len(other) == len(self):
            new_data = copy.copy(self)
            for ind_dfp in range(len(self)):
                new_data[ind_dfp] = self[ind_dfp].average(other[ind_dfp], weight)
            return new_data
        else:
            raise TypeError(f'Could not average a {other.__class__.__name__} with a {self.__class__.__name__} '
                            f'of a different length')

    def merge_as_dwa(self, dim: Union[str, DataDim], name: str = None) -> DataRaw:
        """ attempt to merge filtered dwa into one

        Only possible if all filtered dwa and underlying data have same shape

        Parameters
        ----------
        dim: DataDim or str
            will only try to merge dwa having this dimensionality
        name: str
            The new name of the returned dwa
        """
        dim = enum_checker(DataDim, dim)

        filtered_data = self.get_data_from_dim(dim)
        if len(filtered_data) != 0:
            dwa = filtered_data[0].deepcopy()
            for dwa_tmp in filtered_data[1:]:
                if dwa_tmp.shape == dwa.shape and dwa_tmp.distribution == dwa.distribution:
                    dwa.append(dwa_tmp)
            if name is None:
                name = self.name
            dwa.name = name
            return dwa

    def __repr__(self):
        repr = f'{self.__class__.__name__}: {self.name} <len:{len(self)}>\n'
        for dwa in self:
            repr += f'    * {str(dwa)}\n'
        return repr

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        self._iter_index = 0
        return self

    def __next__(self) -> DataWithAxes:
        if self._iter_index < len(self):
            self._iter_index += 1
            return self.data[self._iter_index-1]
        else:
            raise StopIteration

    def __getitem__(self, item) -> Union[DataWithAxes, DataToExport]:
        if isinstance(item, int) and 0 <= item < len(self):
            return self.data[item]
        elif isinstance(item, slice):
            return DataToExport(self.name, data=[self[ind] for ind in list(range(len(self))[item])])
        else:
            raise IndexError(f'The index should be a positive integer lower than the data length')

    def __setitem__(self, key, value: DataWithAxes):
        if isinstance(key, int) and 0 <= key < len(self) and isinstance(value, DataWithAxes):
            self.data[key] = value
        else:
            raise IndexError(f'The index should be a positive integer lower than the data length')

    def get_names(self, dim: DataDim = None) -> List[str]:
        """Get the names of the stored DataWithAxes,  eventually filtered by dim

        Parameters
        ----------
        dim: DataDim or str

        Returns
        -------
        list of str: the names of the (filtered) DataWithAxes data
        """
        if dim is None:
            return [data.name for data in self.data]
        else:
            return [data.name for data in self.get_data_from_dim(dim).data]

    def get_full_names(self, dim: DataDim = None):
        """Get the ful names including the origin attribute into the returned value,  eventually filtered by dim

        Parameters
        ----------
        dim: DataDim or str

        Returns
        -------
        list of str: the names of the (filtered) DataWithAxes data constructed as : origin/name

        Examples
        --------
        d0 = DataWithAxes(name='datafromdet0', origin='det0')
        """
        if dim is None:
            return [data.get_full_name() for data in self.data]
        else:
            return [data.get_full_name() for data in self.get_data_from_dim(dim).data]

    def get_origins(self, dim: DataDim = None):
        """Get the origins of the underlying data into the returned value,  eventually filtered by dim

        Parameters
        ----------
        dim: DataDim or str

        Returns
        -------
        list of str: the origins of the (filtered) DataWithAxes data

        Examples
        --------
        d0 = DataWithAxes(name='datafromdet0', origin='det0')
        """
        if dim is None:
            return list({dwa.origin for dwa in self.data})
        else:
            return list({dwa.origin for dwa in self.get_data_from_dim(dim).data})


    def get_data_from_full_name(self, full_name: str, deepcopy=False) -> DataWithAxes:
        """Get the DataWithAxes with matching full name"""
        if deepcopy:
            data = self.get_data_from_name_origin(full_name.split('/')[1], full_name.split('/')[0]).deepcopy()
        else:
            data = self.get_data_from_name_origin(full_name.split('/')[1], full_name.split('/')[0])
        return data

    def get_data_from_full_names(self, full_names: List[str], deepcopy=False) -> DataToExport:
        data = [self.get_data_from_full_name(full_name, deepcopy) for full_name in full_names]
        return DataToExport(name=self.name, data=data)

    def get_dim_presents(self) -> List[str]:
        dims = []
        for dim in DataDim.names():
            if len(self.get_data_from_dim(dim)) != 0:
                dims.append(dim)

        return dims

    def get_data_from_source(self, source: DataSource, deepcopy=False) -> DataToExport:
        """Get the data matching the given DataSource

        Returns
        -------
        DataToExport: filtered with data matching the dimensionality
        """
        source = enum_checker(DataSource, source)
        return self.get_data_from_attribute('source', source, deepcopy=deepcopy)

    def get_data_from_missing_attribute(self, attribute: str, deepcopy=False) -> DataToExport:
        """ Get the data matching a given attribute value

        Parameters
        ----------
        attribute: str
            a string of a possible attribute
        deepcopy: bool
            if True the returned DataToExport will contain deepcopies of the DataWithAxes
        Returns
        -------
        DataToExport: filtered with data missing the given attribute
        """
        if deepcopy:
            return DataToExport(self.name, data=[dwa.deepcopy() for dwa in self if not hasattr(dwa, attribute)])
        else:
            return DataToExport(self.name, data=[dwa for dwa in self if not hasattr(dwa, attribute)])

    def get_data_from_attribute(self, attribute: str, attribute_value: Any, deepcopy=False) -> DataToExport:
        """Get the data matching a given attribute value

        Returns
        -------
        DataToExport: filtered with data matching the attribute presence and value
        """
        selection = find_objects_in_list_from_attr_name_val(self.data, attribute, attribute_value,
                                                            return_first=False)
        selection.sort(key=lambda elt: elt[0].name)
        if deepcopy:
            data = [sel[0].deepcopy() for sel in selection]
        else:
            data = [sel[0] for sel in selection]
        return DataToExport(name=self.name, data=data)

    def get_data_from_dim(self, dim: DataDim, deepcopy=False) -> DataToExport:
        """Get the data matching the given DataDim

        Returns
        -------
        DataToExport: filtered with data matching the dimensionality
        """
        dim = enum_checker(DataDim, dim)
        return self.get_data_from_attribute('dim', dim, deepcopy=deepcopy)

    def get_data_from_dims(self, dims: List[DataDim], deepcopy=False) -> DataToExport:
        """Get the data matching the given DataDim

        Returns
        -------
        DataToExport: filtered with data matching the dimensionality
        """
        data = DataToExport(name=self.name)
        for dim in dims:
            data.append(self.get_data_from_dim(dim, deepcopy=deepcopy))
        return data

    def get_data_from_sig_axes(self, Naxes: int, deepcopy: bool = False) -> DataToExport:
        """Get the data matching the given number of signal axes

        Parameters
        ----------
        Naxes: int
            Number of signal axes in the DataWithAxes objects

        Returns
        -------
        DataToExport: filtered with data matching the number of signal axes
        """
        data = DataToExport(name=self.name)
        for _data in self:
            if len(_data.sig_indexes) == Naxes:
                if deepcopy:
                    data.append(_data.deepcopy())
                else:
                    data.append(_data)
        return data

    def get_data_from_Naxes(self, Naxes: int, deepcopy: bool = False) -> DataToExport:
        """Get the data matching the given number of axes

        Parameters
        ----------
        Naxes: int
            Number of axes in the DataWithAxes objects

        Returns
        -------
        DataToExport: filtered with data matching the number of axes
        """
        data = DataToExport(name=self.name)
        for _data in self:
            if len(_data.shape) == Naxes:
                if deepcopy:
                    data.append(_data.deepcopy())
                else:
                    data.append(_data)
        return data

    def get_data_with_naxes_lower_than(self, n_axes=2, deepcopy: bool = False) -> DataToExport:
        """Get the data with n axes lower than the given number

        Parameters
        ----------
        Naxes: int
            Number of axes in the DataWithAxes objects

        Returns
        -------
        DataToExport: filtered with data matching the number of axes
        """
        data = DataToExport(name=self.name)
        for _data in self:
            if _data.n_axes <= n_axes:
                if deepcopy:
                    data.append(_data.deepcopy())
                else:
                    data.append(_data)
        return data

    def get_data_from_name(self, name: str) -> DataWithAxes:
        """Get the data matching the given name"""
        data, _ = find_objects_in_list_from_attr_name_val(self.data, 'name', name, return_first=True)
        return data

    def get_data_from_names(self, names: List[str]) -> DataToExport:
        return DataToExport(self.name, data=[dwa for dwa in self if dwa.name in names])

    def get_data_from_name_origin(self, name: str, origin: str = '') -> DataWithAxes:
        """Get the data matching the given name and the given origin"""
        if origin == '':
            data, _ = find_objects_in_list_from_attr_name_val(self.data, 'name', name, return_first=True)
        else:
            selection = find_objects_in_list_from_attr_name_val(self.data, 'name', name, return_first=False)
            selection = [sel[0] for sel in selection]
            data, _ = find_objects_in_list_from_attr_name_val(selection, 'origin', origin)
        return data

    def index(self, data: DataWithAxes):
        return self.data.index(data)

    def index_from_name_origin(self, name: str, origin: str = '') -> List[DataWithAxes]:
        """Get the index of a given DataWithAxes within the list of data"""
        """Get the data matching the given name and the given origin"""
        if origin == '':
            _, index = find_objects_in_list_from_attr_name_val(self.data, 'name', name, return_first=True)
        else:
            selection = find_objects_in_list_from_attr_name_val(self.data, 'name', name, return_first=False)
            data_selection = [sel[0] for sel in selection]
            index_selection = [sel[1] for sel in selection]
            _, index = find_objects_in_list_from_attr_name_val(data_selection, 'origin', origin)
            index = index_selection[index]
        return index

    def pop(self, index: int) -> DataWithAxes:
        """return and remove the DataWithAxes referred by its index

        Parameters
        ----------
        index: int
            index as returned by self.index_from_name_origin

        See Also
        --------
        index_from_name_origin
        """
        return self.data.pop(index)

    def remove(self, dwa: DataWithAxes):
        return self.pop(self.data.index(dwa))

    @property
    def data(self) -> List[DataWithAxes]:
        """List[DataWithAxes]: get the data contained in the object"""
        return self._data

    @data.setter
    def data(self, new_data: List[DataWithAxes]):
        for dat in new_data:
            self._check_data_type(dat)
        self._data[:] = [dat for dat in new_data]  # shallow copyto make sure that if the original
        # list is changed, the change will not be applied in here

        self.affect_name_to_origin_if_none()

    @staticmethod
    def _check_data_type(data: DataWithAxes):
        """Make sure data is a DataWithAxes object or inherited"""
        if not isinstance(data, DataWithAxes):
            raise TypeError('Data stored in a DataToExport object should be objects inherited from DataWithAxis')

    def deepcopy(self):
        return DataToExport('Copy', data=[data.deepcopy() for data in self])

    @dispatch(list)
    def append(self, data_list: List[DataWithAxes]):
        for dwa in data_list:
            self.append(dwa)

    @dispatch(DataWithAxes)
    def append(self, dwa: DataWithAxes):
        """Append/replace DataWithAxes object to the data attribute

        Make sure only one DataWithAxes object with a given name is in the list except if they don't have the same
        origin identifier
        """
        dwa = dwa.deepcopy()
        self._check_data_type(dwa)
        obj = self.get_data_from_name_origin(dwa.name, dwa.origin)
        if obj is not None:
            self._data.pop(self.data.index(obj))
        self._data.append(dwa)

    @dispatch(object)
    def append(self, dte: DataToExport):
        if isinstance(dte, DataToExport):
            self.append(dte.data)


class DataScan(DataToExport):
    """Specialized DataToExport.To be used for data to be saved """
    def __init__(self, name: str, data: List[DataWithAxes] = [], **kwargs):
        super().__init__(name, data, **kwargs)


class DataToActuators(DataToExport):
    """ Particular case of a DataToExport adding one named parameter to indicate what kind of change
    should be applied to the actuators, absolute or relative

    Attributes
    ----------
    mode: str
        Adds an attribute called mode holding a string describing the type of change:
        relative or absolute

    Parameters
    ---------
    mode: str
        either 'rel' or 'abs' for a relative or absolute change of the actuator's values
    """

    def __init__(self, *args, mode='rel', **kwargs):
        if mode not in ['rel', 'abs']:
            warnings.warn('Incorrect mode for the actuators, switching to default relative mode: rel')
            mode = 'rel'
        kwargs.update({'mode': mode})
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return f'{super().__repr__()}: {self.mode}'



if __name__ == '__main__':
    d = DataRaw('hjk', units='m', data=[np.array([0, 1, 2])])
    dm = DataRaw('hjk', units='mm', data=[np.array([0, 1, 2])])
    d + d
    d - d

    d1 = DataFromRoi(name=f'Hlineout_', data=[np.zeros((24,))],
                     x_axis=Axis(data=np.zeros((24,)), units='myunits', label='mylabel1'))
    d2 = DataFromRoi(name=f'Hlineout_', data=[np.zeros((12,))],
                     x_axis=Axis(data=np.zeros((12,)),
                                 units='myunits2',
                                 label='mylabel2'))

    Nsig = 200
    Nnav = 10
    x = np.linspace(-Nsig/2, Nsig/2-1, Nsig)

    dat = np.zeros((Nnav, Nsig))
    for ind in range(Nnav):
        dat[ind] = mutils.gauss1D(x,  50 * (ind -Nnav / 2), 25 / np.sqrt(2))

    data = DataRaw('mydata', data=[dat], nav_indexes=(0,),
                   axes=[Axis('nav', data=np.linspace(0, Nnav-1, Nnav), index=0),
                         Axis('sig', data=x, index=1)])

    data + data

    data2 = copy.copy(data)

    data3 = data.deepcopy_with_new_data([np.sum(dat, 1)], remove_axes_index=(1,))

    print('done')

