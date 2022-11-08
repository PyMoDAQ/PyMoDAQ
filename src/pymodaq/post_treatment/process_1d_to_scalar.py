# -*- coding: utf-8 -*-
"""
Created the 04/11/2022

@author: Sebastien Weber
"""
import numpy as np
from numbers import Number
from typing import List, Tuple
from abc import ABCMeta, abstractmethod

from pymodaq.utils.factory import ObjectFactory
from pymodaq.utils import math_utils as mutils
from pymodaq.utils.data import DataWithAxes, Axis, DataRaw, DataBase


config_processors = {
}


class Data1DProcessorFactory(ObjectFactory):
    def get(self, processor_name, **kwargs):
        return self.create(processor_name, **kwargs)

    @property
    def functions(self):
        return self.keys


class Data1DProcessorBase(metaclass=ABCMeta):

    def process(self, limits: Tuple[float], data: DataWithAxes):
        axis = data.axes_manager.get_signal_axes()[0]
        (ind_1, _), (ind_2, _) = mutils.find_index(axis.data, limits)
        subdata = data.isig[ind_1:ind_2]
        return subdata, self.operate(subdata)

    @abstractmethod
    def operate(self, sub_data: DataWithAxes):
        pass


class MeanProcessor(Data1DProcessorBase):
    def operate(self, sub_data):
        data_arrays = [np.mean(data, axis=sub_data.axes_manager.sig_indexes) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.axes_manager.sig_indexes)


class StdProcessor(Data1DProcessorBase):
    def operate(self, sub_data):
        data_arrays = [np.std(data, axis=sub_data.axes_manager.sig_indexes) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.axes_manager.sig_indexes)


class SumProcessor(Data1DProcessorBase):
    def operate(self, sub_data):
        data_arrays = [np.sum(data, axis=sub_data.axes_manager.sig_indexes) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.axes_manager.sig_indexes)


class MaxProcessor(Data1DProcessorBase):
    def operate(self, sub_data):
        data_arrays = [np.max(data, axis=sub_data.axes_manager.sig_indexes) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.axes_manager.sig_indexes)


class MinProcessor(Data1DProcessorBase):
    def operate(self, sub_data):
        data_arrays = [np.min(data, axis=sub_data.axes_manager.sig_indexes) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.axes_manager.sig_indexes)


class ArgMaxProcessor(Data1DProcessorBase):
    def process(self, limits: Tuple[int], data: DataWithAxes):
        axis = data.axes_manager.get_signal_axes()[0]
        (ind_1, _), (ind_2, _) = mutils.find_index(axis.data, limits)
        subdata = data.isig[ind_1:ind_2]
        filtered_data = self.operate(subdata)
        filtered_data.data = [data_array + ind_1 for data_array in filtered_data.data]
        return subdata, filtered_data

    def operate(self, sub_data):
        data_arrays = [np.atleast_1d(np.argmax(data, axis=sub_data.axes_manager.sig_indexes[0])) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.axes_manager.sig_indexes)


class ArgMinProcessor(Data1DProcessorBase):
    def process(self, limits: Tuple[int], data: DataWithAxes):
        axis = data.axes_manager.get_signal_axes()[0]
        (ind_1, _), (ind_2, _) = mutils.find_index(axis.data, limits)
        subdata = data.isig[ind_1:ind_2]
        filtered_data = self.operate(subdata)
        filtered_data.data = [data_array + ind_1 for data_array in filtered_data.data]
        return subdata, filtered_data

    def operate(self, sub_data):
        data_arrays = [np.atleast_1d(np.argmin(data, axis=sub_data.axes_manager.sig_indexes[0])) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.axes_manager.sig_indexes)


class HalfLifeProcessor(Data1DProcessorBase):
    #todo Write it properly
    def process(self, limits: Tuple[int], data: DataWithAxes):
        axis = data.axes_manager.get_signal_axes()[0]
        (ind_1, _), (ind_2, _) = mutils.find_index(axis.data, limits)
        subdata = data.isig[ind_1:ind_2]
        return subdata, self.operate(subdata) + limits[0]

    def operate(self, sub_data):
        ind_x0 = mutils.find_index(sub_data, np.max(sub_data))[0][0]
        x0 = sub_axis[ind_x0]
        sub_xaxis = sub_axis[ind_x0:]
        sub_data = sub_data[ind_x0:]
        offset = sub_data[-1]
        N0 = np.max(sub_data) - offset
        return sub_xaxis[mutils.find_index(sub_data - offset, 0.5 * N0)[0][0]] - x0


class ExpoDecayProcessor(Data1DProcessorBase):
    #todo Write it properly
    def process(self, limits: Tuple[int], data: DataWithAxes):
        subdata = data.isig[slice(*limits)]
        return subdata, self.operate(subdata) + limits[0]

    def operate(self, sub_data):
        ind_x0 = mutils.find_index(sub_data, np.max(sub_data))[0][0]
        x0 = sub_axis[ind_x0]
        sub_xaxis = sub_axis[ind_x0:]
        sub_data = sub_data[ind_x0:]
        offset = sub_data[-1]
        N0 = np.max(sub_data) - offset
        return sub_xaxis[mutils.find_index(sub_data - offset, 0.37 * N0)[0][0]] - x0


class FWHMProcessor(Data1DProcessorBase):
    #todo Write it properly
    def process(self, limits: Tuple[int], data: DataWithAxes):
        subdata = data.isig[slice(*limits)]
        return subdata, self.operate(subdata) + limits[0]

    def operate(self, sub_data):
        sub_data = sub_data - np.min(sub_data)
        ind_x0, value = mutils.find_index(sub_data, np.max(sub_data))[0]
        ind_x0m, fwhm_value = mutils.find_index(sub_data, value / 2)[0]

        fwhm = (sub_axis[ind_x0] - sub_axis[ind_x0m]) * 2
        return fwhm


@Data1DProcessorFactory.register('mean')
def create_mean_processor(**_ignored):
    return MeanProcessor()


@Data1DProcessorFactory.register('std')
def create_std_processor(**_ignored):
    return StdProcessor()


@Data1DProcessorFactory.register('max')
def create_max_processor(**_ignored):
    return MaxProcessor()


@Data1DProcessorFactory.register('min')
def create_min_processor(**_ignored):
    return MinProcessor()


@Data1DProcessorFactory.register('argmax')
def create_max_processor(**_ignored):
    return ArgMaxProcessor()


@Data1DProcessorFactory.register('argmin')
def create_min_processor(**_ignored):
    return ArgMinProcessor()


@Data1DProcessorFactory.register('sum')
def create_sum_processor(**_ignored):
    return SumProcessor()


#@Data1DProcessorFactory.register('half-life')
def create_half_life_processor(**_ignored):
    return HalfLifeProcessor()


#@Data1DProcessorFactory.register('expo-decay')
def create_expo_decay_processor(**_ignored):
    return ExpoDecayProcessor()


#@Data1DProcessorFactory.register('fwhm')
def create_expo_decay_processor(**_ignored):
    return FWHMProcessor()


if __name__ == '__main__':
    processors = Data1DProcessorFactory()
    print('Builders:\n'
          f'{processors.builders}')

    print('Math functions:\n'
          f'{processors.functions}')

    # tests 1D signal
    Nsig = 200
    Nnav = 10
    x = np.linspace(-Nsig/2, Nsig/2-1, Nsig)

    dat = np.zeros((Nnav, Nsig))
    for ind in range(Nnav):
        dat[ind] = ind * mutils.gauss1D(x,  10 * (ind -Nnav / 2), 25 / np.sqrt(2))

    data = DataRaw('mydata', data=[dat], nav_indexes=(0,),
                   axes=[Axis('nav', data=np.linspace(0, Nnav-1, Nnav), index=0),
                         Axis('sig', data=x, index=1)])

    filtered_data, new_data = processors.get('max', **config_processors).process((-50, 50), data)
    print(new_data)
    print(new_data.data)




