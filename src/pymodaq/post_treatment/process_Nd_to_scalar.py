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
        return self.keys


class DataNDProcessorBase(metaclass=ABCMeta):
    """Apply processing functions to signal data. This function should return a scalar.
    """

    def process(self, data: DataWithAxes):
        return self.operate(data)

    @abstractmethod
    def operate(self, sub_data: DataWithAxes):
        pass

    def __call__(self, **kwargs):
        return self(**kwargs)


@DataNDProcessorFactory.register('mean')
class MeanProcessor(DataNDProcessorBase):
    def operate(self, sub_data: DataWithAxes):
        data_arrays = [np.mean(data, axis=sub_data.axes_manager.sig_indexes) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.axes_manager.sig_indexes)


@DataNDProcessorFactory.register('std')
class StdProcessor(DataNDProcessorBase):
    def operate(self, sub_data: DataWithAxes):
        data_arrays = [np.std(data, axis=sub_data.axes_manager.sig_indexes) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.axes_manager.sig_indexes)


@DataNDProcessorFactory.register('sum')
class SumProcessor(DataNDProcessorBase):
    def operate(self, sub_data: DataWithAxes):
        data_arrays = [np.sum(data, axis=sub_data.axes_manager.sig_indexes) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.axes_manager.sig_indexes)


@DataNDProcessorFactory.register('max')
class MaxProcessor(DataNDProcessorBase):
    def operate(self, sub_data: DataWithAxes):
        data_arrays = [np.max(data, axis=sub_data.axes_manager.sig_indexes) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.axes_manager.sig_indexes)


@DataNDProcessorFactory.register('min')
class MinProcessor(DataNDProcessorBase):
    def operate(self, sub_data: DataWithAxes):
        data_arrays = [np.min(data, axis=sub_data.axes_manager.sig_indexes) for data in sub_data]
        return sub_data.deepcopy_with_new_data(data_arrays, sub_data.axes_manager.sig_indexes)


if __name__ == '__main__':
    import copy
    processors = DataNDProcessorFactory()
    print('Builders:\n'
          f'{processors.builders}')

    print('Math functions:\n'
          f'{processors.functions}')

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
