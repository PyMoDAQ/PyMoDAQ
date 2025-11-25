# -*- coding: utf-8 -*-
"""
Created the 04/11/2022

@author: Sebastien Weber
"""
import numpy as np
from numbers import Number
from typing import List, Tuple
from abc import ABCMeta, abstractmethod, abstractproperty

from pymodaq_utils.factory import ObjectFactory
from pymodaq_utils import math_utils as mutils
from pymodaq_data.data import DataWithAxes, Axis, DataRaw, DataBase, DataDim, DataCalculated


config_processors = {
}


class DataProcessorBase(metaclass=ABCMeta):
    """Apply processing functions to signal data. This function should return a DataWithAxes.

    Attributes
    ----------
    apply_to: DataDim
        Specify on which type of data dimensionality this processor can be applied to, if only 1D:
        apply_to = DataDim['Data1D']

    """

    apply_to: DataDim = abstractproperty

    def process(self, data: DataWithAxes) -> DataWithAxes:
        return self.operate(data)

    @abstractmethod
    def operate(self, sub_data: DataWithAxes):
        pass

    @staticmethod
    def flatten_signal_dim(sub_data: DataWithAxes) -> Tuple[Tuple, np.ndarray]:
        """flattens data's ndarrays along the signal dimensions"""
        data_arrays = []
        new_shape = [sub_data.shape[ind] for ind in sub_data.nav_indexes]
        new_shape.append(np.prod([sub_data.shape[ind] for ind in sub_data.sig_indexes]))

        # for each data in subdata, apply the function, here argmax, along the flattened dimension. Then unravel the
        # possible multiple indexes (1 for 1D, 2 for 2D)
        for ind, data in enumerate(sub_data):
            data_arrays.append(data.reshape(new_shape))
        return new_shape, data_arrays

    def __call__(self, **kwargs):
        return self(**kwargs)


class DataProcessorFactory(ObjectFactory):
    def get(self, processor_name, **kwargs) -> DataProcessorBase:
        return self.create(processor_name, **kwargs)

    @property
    def functions(self):
        """Get the list of processor functions"""
        return self.keys_function(do_sort=False)

    def functions_filtered(self, dim: DataDim):
        """Get the list of processor functions that could be applied to data having a given dimensionality"""
        return [key for key in self.functions if self.get(key).apply_to >= dim]


@DataProcessorFactory.register('mean')
class MeanProcessor(DataProcessorBase):
    apply_to = DataDim['DataND']

    def operate(self, sub_data: DataWithAxes):
        data_arrays = [np.atleast_1d(np.mean(data, axis=sub_data.sig_indexes)) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.sig_indexes)


@DataProcessorFactory.register('std')
class StdProcessor(DataProcessorBase):
    apply_to = DataDim['DataND']

    def operate(self, sub_data: DataWithAxes):
        data_arrays = [np.atleast_1d(np.std(data, axis=sub_data.sig_indexes)) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.sig_indexes)


@DataProcessorFactory.register('sum')
class SumProcessor(DataProcessorBase):
    apply_to = DataDim['DataND']

    def operate(self, sub_data: DataWithAxes):
        data_arrays = [np.atleast_1d(np.sum(data, axis=sub_data.sig_indexes)) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.sig_indexes)


@DataProcessorFactory.register('max')
class MaxProcessor(DataProcessorBase):
    apply_to = DataDim['DataND']

    def operate(self, sub_data: DataWithAxes):
        data_arrays = [np.atleast_1d(np.max(data, axis=sub_data.sig_indexes)) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.sig_indexes)


@DataProcessorFactory.register('min')
class MinProcessor(DataProcessorBase):
    apply_to = DataDim['DataND']

    def operate(self, sub_data: DataWithAxes):
        data_arrays = [np.atleast_1d(np.min(data, axis=sub_data.sig_indexes)) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.sig_indexes)


@DataProcessorFactory.register('argmax')
class ArgMaxProcessor(DataProcessorBase):
    apply_to = DataDim['DataND']

    def operate(self, sub_data: DataWithAxes):
        """Extract info from sub-DataWithAxes

        Retrieve the signal axis values of the maximum position of the data

        Notes
        -----
        For more complex processors, such as the argmin, argmax ... , one cannot use directly the numpy function
        (compared to min, max, mean...). Indeed one has to first flatten the data arrays on the signal axes, then apply
        the function on the flatten dimension, here get the indexes of the minimum along the flattened dimension (as
        a function of the eventual navigations dimensions). From this index, on then obtain as many indexes as signal
        dimensions (1 for 1D Signals, 2 for 2D signals). And we do this for as many data there is in sub_data.
        """
        new_data_arrays = []
        new_shape, flattened_arrays = self.flatten_signal_dim(sub_data)

        for dat in flattened_arrays:
            indexes = np.unravel_index(np.nanargmax(dat, len(new_shape)-1), sub_data.shape)[len(sub_data.nav_indexes):]
            # from the unraveled index, retrieve the corresponding axis value
            for ind in range(len(indexes)):
                axis_data = sub_data.get_axis_from_index(sub_data.sig_indexes[ind])[0].get_data()
                new_data_arrays.append(np.atleast_1d(axis_data[indexes[ind]]))
        return DataCalculated('processed_data', data=new_data_arrays, nav_indexes=sub_data.nav_indexes,
                              axes=[axis for axis in sub_data.axes if axis.index in sub_data.nav_indexes],
                              distribution=sub_data.distribution)


@DataProcessorFactory.register('argmin')
class ArgMinProcessor(DataProcessorBase):
    apply_to = DataDim['DataND']

    def operate(self, sub_data: DataWithAxes):
        """Extract info from sub-DataWithAxes

        Retrieve the signal axis values of the minimum position of the data

        Notes
        -----
        For more complex processors, such as the argmin, argmax ... , one cannot use directly the numpy function
        (compared to min, max, mean...). Indeed one has to first flatten the data arrays on the signal axes, then apply
        the function on the flatten dimension, here get the indexes of the minimum along the flattened dimension (as
        a function of the eventual navigations dimensions). From this index, on then obtain as many indexes as signal
        dimensions (1 for 1D Signals, 2 for 2D signals). And we do this for as many data there is in sub_data.
        """
        new_data_arrays = []
        new_shape, flattened_arrays = self.flatten_signal_dim(sub_data)

        for dat in flattened_arrays:
            indexes = np.unravel_index(np.nanargmin(dat, len(new_shape)-1), sub_data.shape)[len(sub_data.nav_indexes):]
            # from the unraveled index, retrieve the corresponding axis value
            for ind in range(len(indexes)):
                axis_data = sub_data.get_axis_from_index(sub_data.sig_indexes[ind])[0].get_data()
                new_data_arrays.append(np.atleast_1d(axis_data[indexes[ind]]))
        return DataCalculated('processed_data', data=new_data_arrays, nav_indexes=sub_data.nav_indexes,
                              axes=[axis for axis in sub_data.axes if axis.index in sub_data.nav_indexes],
                              distribution=sub_data.distribution)


@DataProcessorFactory.register('argmean')
class ArgMeanProcessor(DataProcessorBase):
    apply_to = DataDim['Data1D']

    def operate(self, sub_data: DataWithAxes):
        """Extract info from sub-DataWithAxes

        Retrieve the signal mean axis values

        Notes
        -----
        For more complex processors, such as the argmin, argmax ... , one cannot use directly the numpy function
        (compared to min, max, mean...). Indeed one has to first flatten the data arrays on the signal axes, then apply
        the function on the flatten dimension, here get the indexes of the minimum along the flattened dimension (as
        a function of the eventual navigations dimensions). From this index, on then obtain as many indexes as signal
        dimensions (1 for 1D Signals, 2 for 2D signals). And we do this for as many data there is in sub_data.
        """
        new_data_arrays = []
        new_shape, flattened_arrays = self.flatten_signal_dim(sub_data)
        values = sub_data.get_axis_from_index(sub_data.sig_indexes[0])[0].get_data()
        for dat in flattened_arrays:
            weights = dat
            new_data_arrays.append(np.atleast_1d(np.average(values, axis=len(new_shape) - 1, weights=weights)))
        return DataCalculated('processed_data', data=new_data_arrays, nav_indexes=sub_data.nav_indexes,
                              axes=[axis for axis in sub_data.axes if axis.index in sub_data.nav_indexes])


@DataProcessorFactory.register('argstd')
class ArgStdProcessor(DataProcessorBase):
    apply_to = DataDim['Data1D']

    def operate(self, sub_data: DataWithAxes):
        """Extract info from sub-DataWithAxes

        Retrieve the signal mean axis values

        Notes
        -----
        For more complex processors, such as the argmin, argmax ... , one cannot use directly the numpy function
        (compared to min, max, mean...). Indeed one has to first flatten the data arrays on the signal axes, then apply
        the function on the flatten dimension, here get the indexes of the minimum along the flattened dimension (as
        a function of the eventual navigations dimensions). From this index, on then obtain as many indexes as signal
        dimensions (1 for 1D Signals, 2 for 2D signals). And we do this for as many data there is in sub_data.
        """
        new_data_arrays = []
        new_shape, flattened_arrays = self.flatten_signal_dim(sub_data)
        values = sub_data.get_axis_from_index(sub_data.sig_indexes[0])[0].get_data()
        for dat in flattened_arrays:
            weights = dat
            w_avg = np.atleast_1d(np.average(values, axis=len(new_shape) - 1, weights=weights))
            new_data_arrays.append(np.atleast_1d(np.sqrt(
                np.sum(weights * (values - w_avg) ** 2, axis=len(new_shape) - 1) /
                np.sum(weights, axis=len(new_shape) - 1))))
        return DataCalculated('processed_data', data=new_data_arrays, nav_indexes=sub_data.nav_indexes,
                              axes=[axis for axis in sub_data.axes if axis.index in sub_data.nav_indexes])

