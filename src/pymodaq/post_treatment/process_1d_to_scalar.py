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


config_processors = {
}


class Data1DProcessorFactory(ObjectFactory):
    def get(self, processor_name, **kwargs):
        return self.create(processor_name, **kwargs)

    @property
    def functions(self):
        return list(self.builders.keys())


class Data1DProcessorBase(metaclass=ABCMeta):

    def process(self, limits: List, axis: np.ndarray, data: np.ndarray):
        indexes = mutils.find_index(axis, limits)
        ind1 = indexes[0][0]
        ind2 = indexes[1][0]
        sub_data = data[ind1:ind2]
        sub_axis = axis[ind1:ind2]
        return sub_axis, sub_data, self.operate(sub_axis, sub_data, operation_axis=-1)

    @abstractmethod
    def operate(self, sub_axis, sub_data, operation_axis=-1):
        pass


class MeanProcessor(Data1DProcessorBase):
    def operate(self, sub_axis, sub_data, operation_axis=-1):
        return np.mean(sub_data, axis=operation_axis)


class StdProcessor(Data1DProcessorBase):
    def operate(self, sub_data, sub_axis, operation_axis=-1):
        return np.std(sub_data, axis=operation_axis)


class SumProcessor(Data1DProcessorBase):
    def operate(self, sub_axis, sub_data, operation_axis=-1):
        return np.sum(sub_data, axis=operation_axis)


class MaxProcessor(Data1DProcessorBase):
    def operate(self, sub_axis, sub_data, operation_axis=-1):
        return np.max(sub_data, axis=operation_axis)


class MinProcessor(Data1DProcessorBase):
    def operate(self, sub_axis, sub_data, operation_axis=-1):
        return np.min(sub_data, axis=operation_axis)


class HalfLifeProcessor(Data1DProcessorBase):
    def operate(self, sub_axis, sub_data, operation_axis=-1):
        ind_x0 = mutils.find_index(sub_data, np.max(sub_data))[0][0]
        x0 = sub_axis[ind_x0]
        sub_xaxis = sub_axis[ind_x0:]
        sub_data = sub_data[ind_x0:]
        offset = sub_data[-1]
        N0 = np.max(sub_data) - offset
        return sub_xaxis[mutils.find_index(sub_data - offset, 0.5 * N0)[0][0]] - x0


class ExpoDecayProcessor(Data1DProcessorBase):
    def operate(self, sub_axis, sub_data, operation_axis=-1):
        ind_x0 = mutils.find_index(sub_data, np.max(sub_data))[0][0]
        x0 = sub_axis[ind_x0]
        sub_xaxis = sub_axis[ind_x0:]
        sub_data = sub_data[ind_x0:]
        offset = sub_data[-1]
        N0 = np.max(sub_data) - offset
        return sub_xaxis[mutils.find_index(sub_data - offset, 0.37 * N0)[0][0]] - x0


class FWHMProcessor(Data1DProcessorBase):
    def operate(self, sub_axis, sub_data, operation_axis=-1):
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


@Data1DProcessorFactory.register('sum')
def create_sum_processor(**_ignored):
    return SumProcessor()


@Data1DProcessorFactory.register('half-life')
def create_half_life_processor(**_ignored):
    return HalfLifeProcessor()


@Data1DProcessorFactory.register('expo-decay')
def create_expo_decay_processor(**_ignored):
    return ExpoDecayProcessor()


@Data1DProcessorFactory.register('fwhm')
def create_expo_decay_processor(**_ignored):
    return FWHMProcessor()


processors = Data1DProcessorFactory()


if __name__ == '__main__':
    x = np.linspace(0, 200, 201)
    y1 = mutils.gauss1D(x, 75, 25 / np.sqrt(2))
    y2 = mutils.gauss1D(x, 120, 50, 2)
    tau_half = 27
    x0 = 50
    dx = 20
    ydata_expodec = np.zeros((len(x)))
    ydata_expodec[:50] = 1 * mutils.gauss1D(x[:50], x0, dx, 2)
    ydata_expodec[50:] = 1 * np.exp(-(x[50:] - x0) / (tau_half / np.log(2)))  # +1*np.exp(-(x[50:]-x0)/tau2)
    ydata_expodec += 0.05 * np.random.rand(len(x))

    processors = Data1DProcessorFactory()
    print('Builders:\n'
          f'{processors.builders}')

    print('Math functions:\n'
          f'{processors.functions}')

    print(f"Math_mean: {processors.get('mean', **config_processors).process((0, 200), x, ydata_expodec)[2]}\n"
          f"Mean tot: {np.mean(ydata_expodec)}")
    sum_processor = processors.get('sum', **config_processors)
    sum_processor.process((50, 200), x, ydata_expodec)

    print(f"FWHM should be 25, calculated at :{processors.get('fwhm').process((0, 200), x, y1)[2]}")
