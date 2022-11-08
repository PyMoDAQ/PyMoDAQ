# -*- coding: utf-8 -*-
"""
Created the 04/11/2022

@author: Sebastien Weber
"""
import numpy as np
from numbers import Number
from typing import List
from abc import ABCMeta, abstractmethod

from pymodaq.utils.factory import ObjectFactory
from pymodaq.utils import math_utils as mutils
from pymodaq.utils.data import DataWithAxes, Axis, DataRaw, DataBase


config_processors = {
}


class DataNDProcessorFactory(ObjectFactory):
    def get(self, processor_name, **kwargs):
        return self.create(processor_name, **kwargs)

    @property
    def functions(self):
        return list(self.builders.keys())


class DataNDProcessorBase(metaclass=ABCMeta):
    """Apply processing functions for data with a 1D signal axis """

    def process(self, limits: List, data: DataWithAxes):
        axis = data.axes_manager.get_signal_axes()[0]
        indexes = mutils.find_index(axis.data, limits)
        ind1 = indexes[0][0]
        ind2 = indexes[1][0]
        sub_data = data.isig[ind1:ind2]
        return self.operate(sub_data)

    @abstractmethod
    def operate(self, sub_data: DataWithAxes):
        pass


class MeanProcessor(DataNDProcessorBase):
    def operate(self, sub_data: DataWithAxes):
        data_arrays = [np.mean(data, axis=sub_data.axes_manager.sig_indexes) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.axes_manager.sig_indexes)


class StdProcessor(DataNDProcessorBase):
    def operate(self, sub_data: DataWithAxes):
        data_arrays = [np.std(data, axis=sub_data.axes_manager.sig_indexes) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.axes_manager.sig_indexes)


class SumProcessor(DataNDProcessorBase):
    def operate(self, sub_data: DataWithAxes):
        data_arrays = [np.sum(data, axis=sub_data.axes_manager.sig_indexes) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.axes_manager.sig_indexes)


class MaxProcessor(DataNDProcessorBase):
    def operate(self, sub_data: DataWithAxes):
        data_arrays = [np.max(data, axis=sub_data.axes_manager.sig_indexes) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.axes_manager.sig_indexes)


class MinProcessor(DataNDProcessorBase):
    def operate(self, sub_data: DataWithAxes):
        data_arrays = [np.min(data, axis=sub_data.axes_manager.sig_indexes) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.axes_manager.sig_indexes)


class ArgMaxProcessor(DataNDProcessorBase):
    def operate(self, sub_data: DataWithAxes):
        data_arrays = [np.argmax(data, axis=sub_data.axes_manager.sig_indexes) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.axes_manager.sig_indexes)


class ArgMinProcessor(DataNDProcessorBase):
    def operate(self, sub_data: DataWithAxes):
        data_arrays = [np.argmin(data, axis=sub_data.axes_manager.sig_indexes) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.axes_manager.sig_indexes)


class HalfLifeProcessor(DataNDProcessorBase):
    def operate(self, sub_data: DataWithAxes):
        sub_axis = data.axes_manager.get_signal_axes()[0].data
        ind_x0 = mutils.find_index(sub_data, np.max(sub_data.data[0]))[0][0]
        x0 = sub_axis[ind_x0]
        sub_xaxis = sub_axis[ind_x0:]
        sub_data = sub_data.data[0][ind_x0:]
        offset = sub_data[-1]
        N0 = np.max(sub_data) - offset
        return sub_xaxis[mutils.find_index(sub_data - offset, 0.5 * N0)[0][0]] - x0


class ExpoDecayProcessor(DataNDProcessorBase):
    def operate(self, sub_data: DataWithAxes):
        ind_x0 = mutils.find_index(sub_data, np.max(sub_data.data[0]))[0][0]
        x0 = sub_axis[ind_x0]
        sub_xaxis = sub_axis[ind_x0:]
        sub_data = sub_data[ind_x0:]
        offset = sub_data[-1]
        N0 = np.max(sub_data) - offset
        return sub_xaxis[mutils.find_index(sub_data - offset, 0.37 * N0)[0][0]] - x0


class FWHMProcessor(DataNDProcessorBase):
    def operate(self, sub_data: DataWithAxes, axis_index=-1):
        sub_data = sub_data - np.min(sub_data)
        ind_x0, value = mutils.find_index(sub_data, np.max(sub_data))[0]
        ind_x0m, fwhm_value = mutils.find_index(sub_data, value / 2)[0]

        fwhm = (sub_axis[ind_x0] - sub_axis[ind_x0m]) * 2
        return fwhm


@DataNDProcessorFactory.register('mean')
def create_mean_processor(**_ignored):
    return MeanProcessor()


@DataNDProcessorFactory.register('std')
def create_std_processor(**_ignored):
    return StdProcessor()


@DataNDProcessorFactory.register('max')
def create_max_processor(**_ignored):
    return MaxProcessor()


@DataNDProcessorFactory.register('min')
def create_min_processor(**_ignored):
    return MinProcessor()


@DataNDProcessorFactory.register('sum')
def create_sum_processor(**_ignored):
    return SumProcessor()


#@DataNDProcessorFactory.register('half-life')
def create_half_life_processor(**_ignored):
    return HalfLifeProcessor()


#@DataNDProcessorFactory.register('expo-decay')
def create_expo_decay_processor(**_ignored):
    return ExpoDecayProcessor()


#@DataNDProcessorFactory.register('fwhm')
def create_expo_decay_processor(**_ignored):
    return FWHMProcessor()


if __name__ == '__main__':
    import copy
    processors = DataNDProcessorFactory()
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

    new_data = processors.get('max', **config_processors).process((-50, 50), data)
    print(new_data)
    print(new_data.data)

    # test 2D signals
    Nsigx = 200
    Nsigy = 100
    Nnav = 10
    x = np.linspace(-Nsigx / 2, Nsigx / 2 - 1, Nsigx)
    y = np.linspace(-Nsigy / 2, Nsigy / 2 - 1, Nsigy)

    dat = np.zeros((Nnav, Nsigy, Nsigx))
    for ind in range(Nnav):
        dat[ind] = ind * mutils.gauss2D(x, 10 * (ind - Nnav / 2), 25 / np.sqrt(2),
                                        y, 2 * (ind - Nnav / 2), 10 / np.sqrt(2))

    data = DataRaw('mydata', data=[dat], nav_indexes=(0,),
                   axes=[Axis('nav', data=np.linspace(0, Nnav-1, Nnav), index=0),
                         Axis('sigy', data=y, index=1),
                         Axis('sigx', data=x, index=2)])
    new_data = processors.get('sum', **config_processors).operate(data.isig[25:75, 75:125])
    print(new_data)
    print(new_data.data)
