# -*- coding: utf-8 -*-
"""
Created the 07/11/2022

@author: Sebastien Weber
"""
from typing import Union, List, TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    from pymodaq_data import DataWithAxes, Axis


class SpecialSlicers(object):
    """make it elegant to apply a slice to navigation or signal dimensions"""
    def __init__(self, obj: Union['DataWithAxes', 'Axis'], is_navigation, is_index=True):
        self.is_navigation = is_navigation
        self.is_index = is_index
        self.obj = obj

    def __getitem__(self, slices) -> Union['DataWithAxes', 'Axis']:
        if hasattr(self.obj, 'axes') and self.obj.distribution.name == 'spread' and not self.is_index:
            raise NotImplementedError('Impossible to slice by value a spread data object')
        return self.obj._slicer(slices, self.is_navigation, is_index=self.is_index)


class SpecialSlicersData(SpecialSlicers):

    def __setitem__(self, slices, data: Union[np.ndarray, 'DataWithAxes', 'Axis']):
        """x.__setitem__(slices, data) <==> x[slices]=data
        """
        total_slices, slices_index = self.obj._compute_slices(slices, self.is_navigation, is_index=self.is_index)

        if hasattr(self.obj, 'base_type') and self.obj.base_type == 'Axis':
            if isinstance(data, np.ndarray):
                data_to_replace = data
            else:
                data_to_replace = data.get_data()
            if hasattr(self.obj, 'units') and self.obj.data is None:
                self.obj.create_linear_data(len(self.obj))
            self.obj.data[total_slices] = data_to_replace
        else:
            for ind in range(len(self.obj)):
                if isinstance(data, np.ndarray):
                    data_to_replace = data
                else:  # means it's a DataWithAxes
                    data_to_replace = data[ind]
                self.obj[ind][total_slices] = data_to_replace

    def __len__(self):
        return self.obj.axes_manager.sig_shape[0]
