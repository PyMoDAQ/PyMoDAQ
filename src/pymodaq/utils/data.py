# -*- coding: utf-8 -*-
"""
Created the 27/10/2022

@author: Sebastien Weber
"""
import numbers
from collections import OrderedDict
import numpy as np
from typing import List, Union
import warnings
from time import time


DATASOURCES = ('raw', 'roi')
DATADIMS = ('Data0D', 'Data1D', 'Data2D', 'DataND')


class AxisBase(dict):
    """
    Utility class defining an axis for pymodaq's viewers, attribute can be accessed as dictionary keys or class
    type attribute
    """

    def __init__(self, label='', units='', **kwargs):
        """

        Parameters
        ----------
        data
        label
        units
        """
        if units is None:
            units = ''
        if label is None:
            label = ''
        if not isinstance(label, str):
            raise TypeError('label for the Axis class should be a string')
        self['label'] = label
        if not isinstance(units, str):
            raise TypeError('units for the Axis class should be a string')
        self['units'] = units
        self.update(kwargs)

    def __getattr__(self, item):
        if item in self:
            return self[item]
        else:
            raise AttributeError(f'{item} is not a valid attribute')


class Axis(AxisBase):
    """
    Utility class defining an axis for pymodaq's viewers, attribute can be accessed as dictionary keys
    """

    def __init__(self, data=None, label='', units='', **kwargs):
        """

        Parameters
        ----------
        data
        label
        units
        """
        super().__init__(label=label, units=units, **kwargs)
        if data is None or isinstance(data, np.ndarray):
            self['data'] = data
        else:
            raise TypeError('data for the Axis class should be a ndarray')
        self.update(kwargs)

    def __mul__(self, other):
        if isinstance(other, numbers.Number):
            return Axis(data=self['data'] * other, label=self['label'], units=self['units'])


class NavAxis(Axis):
    def __init__(self, data=None, label='', units='', nav_index=-1, **kwargs):
        super().__init__(data=data, label=label, units=units, **kwargs)

        if nav_index < 0:
            raise ValueError('nav_index should be a positive integer representing the index of this axis among all'
                             'navigation axes')
        self['nav_index'] = nav_index


class ScaledAxis(AxisBase):
    def __init__(self, label='', units='', offset=0, scaling=1):
        super().__init__(label=label, units=units)
        if not (isinstance(offset, float) or isinstance(offset, int)):
            raise TypeError('offset for the ScalingAxis class should be a float (or int)')
        self['offset'] = offset
        if not (isinstance(scaling, float) or isinstance(scaling, int)):
            raise TypeError('scaling for the ScalingAxis class should be a non null float (or int)')
        if scaling == 0 or scaling == 0.:
            raise ValueError('scaling for the ScalingAxis class should be a non null float (or int)')
        self['scaling'] = scaling


class ScalingOptions(dict):
    def __init__(self, scaled_xaxis: ScaledAxis, scaled_yaxis: ScaledAxis):
        assert isinstance(scaled_xaxis, ScaledAxis)
        assert isinstance(scaled_yaxis, ScaledAxis)
        self['scaled_xaxis'] = scaled_xaxis
        self['scaled_yaxis'] = scaled_yaxis


class DataSourceError(Exception):
    pass

class Data(OrderedDict):
    def __init__(self, name='', source='raw', distribution='uniform', x_axis: Axis = None,
                 y_axis: Axis = None, **kwargs):
        """
        Generic class subclassing from OrderedDict defining data being exported from pymodaq's plugin or viewers,
        attribute can be accessed as dictionary keys. Should be subclassed from for real datas
        Parameters
        ----------
        source: str
            either 'raw' or 'roi...' if straight from a plugin or data processed within a viewer
        distribution: str
            either 'uniform' or 'spread'
        x_axis: Axis
            Axis class defining the corresponding axis (if any) (with data either linearly spaced or containing the
            x positions of the spread points)
        y_axis: Axis
            Axis class defining the corresponding axis (if any) (with data either linearly spaced or containing the
            y positions of the spread points)
        """

        if not isinstance(name, str):
            raise TypeError(f'name for the {self.__class__.__name__} class should be a string')
        self['name'] = name
        if not isinstance(source, str):
            raise TypeError(f'source for the {self.__class__.__name__} class should be a string')
        elif not ('raw' in source or 'roi' in source):
            raise ValueError(f'Invalid "source" for the {self.__class__.__name__} class')
        self['source'] = source

        if not isinstance(distribution, str):
            raise TypeError(f'distribution for the {self.__class__.__name__} class should be a string')
        elif distribution not in ('uniform', 'spread'):
            raise ValueError(f'Invalid "distribution" for the {self.__class__.__name__} class')
        self['distribution'] = distribution

        if x_axis is not None:
            if not isinstance(x_axis, Axis):
                if isinstance(x_axis, np.ndarray):
                    x_axis = Axis(data=x_axis)
                else:
                    raise TypeError(f'x_axis for the {self.__class__.__name__} class should be a Axis class')
                self['x_axis'] = x_axis
            elif x_axis['data'] is not None:
                self['x_axis'] = x_axis

        if y_axis is not None:
            if not isinstance(y_axis, Axis):
                if isinstance(y_axis, np.ndarray):
                    y_axis = Axis(data=y_axis)
                else:
                    raise TypeError(f'y_axis for the {self.__class__.__name__} class should be a Axis class')
                self['y_axis'] = y_axis
            elif y_axis['data'] is not None:
                self['y_axis'] = y_axis

        for k in kwargs:
            self[k] = kwargs[k]

    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError(f'{name} if not a key of {self}')

    def __repr__(self):
        return f'{self.__class__.__name__}: <name: {self.name}> - <distribution: {self.distribution}> - <source: {self.source}>'


class DataTimeStamped(Data):
    def __init__(self, acq_time_s: int = 0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self['acq_time_s'] = acq_time_s


class DataFromPlugins(Data):

    def __init__(self, data=None, dim='', labels=[], nav_axes=[], nav_x_axis=Axis(), nav_y_axis=Axis(), **kwargs):
        """
        Parameters
        ----------
        dim: (str) data dimensionality (either Data0D, Data1D, Data2D or DataND)
        """
        super().__init__(**kwargs)
        self['labels'] = labels
        if len(nav_axes) != 0:
            self['nav_axes'] = nav_axes
        if nav_x_axis['data'] is not None:
            self['nav_x_axis'] = nav_x_axis
        if nav_y_axis['data'] is not None:
            self['nav_y_axis'] = nav_y_axis

        iscorrect = True
        if data is not None:
            if isinstance(data, list):
                for dat in data:
                    if not isinstance(dat, np.ndarray):
                        iscorrect = False
            else:
                iscorrect = False

        if iscorrect:
            self['data'] = data
        else:
            raise TypeError('data for the DataFromPlugins class should be None or a list of numpy arrays')

        if dim not in DATADIMS and data is not None:
            ndim = len(data[0].shape)
            if ndim == 1:
                if data[0].size == 1:
                    dim = 'Data0D'
                else:
                    dim = 'Data1D'
            elif ndim == 2:
                dim = 'Data2D'
            else:
                dim = 'DataND'
        self['dim'] = dim

    def __repr__(self):
        return f'{self.__class__.__name__}: <name: {self.name}> - <distribution: {self.distribution}>' \
               f' - <source: {self.source}> - <dim: {self.dim}>'


class DataToEmit(DataTimeStamped):
    """Utility class defining data emitted by DAQ_Viewers or DAQ_Move

    to be precessed by externaly connected object

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_data_0D(self):
        return self['data']['data']


class DataToExport(Data):
    def __init__(self, data=None, dim='', source='raw', **kwargs):
        """
        Utility class defining a data being exported from pymodaq's viewers, attribute can be accessed as dictionary keys
        Parameters
        ----------
        data: (ndarray or a scalar)
        dim: (str) data dimensionality (either Data0D, Data1D, Data2D or DataND)
        source: (str) either 'raw' for raw data or 'roi' for data extracted from a roi
        """
        super().__init__(source=source, **kwargs)
        if data is None or isinstance(data, np.ndarray) or isinstance(data, float) or isinstance(data, int):
            self['data'] = data
        else:
            raise TypeError('data for the DataToExport class should be a scalar or a ndarray')

        if dim not in ('Data0D', 'Data1D', 'Data2D', 'DataND') or data is not None:
            if isinstance(data, np.ndarray):
                ndim = len(data.shape)
                if ndim == 1:
                    if data.size == 1:
                        dim = 'Data0D'
                    else:
                        dim = 'Data1D'
                elif ndim == 2:
                    dim = 'Data2D'
                else:
                    dim = 'DataND'
            else:
                dim = 'Data0D'
        self['dim'] = dim
        if source not in DATASOURCES:
            raise DataSourceError(f'Data source should be in {DATASOURCES}')

    def __repr__(self):
        return f'{self.__class__.__name__}: <name: {self["name"]}> - <distribution: {self["distribution"]}>' \
               f' - <source: {self["source"]}> - <dim: {self["dim"]}>'


def convert_daq_type_data_dim(item: str):
    if item in DATADIMS:
        return f'DAQ{4:}'
    elif 'DAQ' in item:
        return f'Data{3:}'
