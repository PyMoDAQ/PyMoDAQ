# -*- coding: utf-8 -*-
"""
Created the 07/11/2022

@author: Sebastien Weber
"""
from typing import Union, List, TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    from pymodaq.utils.data import DataWithAxes, Axis


class SpecialSlicers(object):
    """make it elegant to apply a slice to navigation or signal dimensions"""
    def __init__(self, obj: Union['DataWithAxes', 'Axis'], is_navigation):
        self.is_navigation = is_navigation
        self.obj = obj

    def __getitem__(self, slices):
        return self.obj._slicer(slices, self.is_navigation)


class SpecialSlicersData(SpecialSlicers):

    def __setitem__(self, slices, data: Union[np.ndarray, 'DataWithAxes', 'Axis']):
        """x.__setitem__(slices, data) <==> x[slices]=data
        """
        slices = self.obj._compute_slices(slices, self.is_navigation)

        if hasattr(self.obj, 'units'):
            if isinstance(data, np.ndarray):
                data_to_replace = data
            else:
                data_to_replace = data.get_data()
            if hasattr(self.obj, 'units') and self.obj.data is None:
                self.obj.create_linear_data(len(self.obj))
            self.obj.data[slices] = data_to_replace
        else:
            for ind in range(len(self.obj)):
                if isinstance(data, np.ndarray):
                    data_to_replace = data
                else:  # means it's a DataWithAxes
                    data_to_replace = data[ind]
                self.obj[ind][slices] = data_to_replace

    def __len__(self):
        return self.obj.axes_manager.sig_shape[0]


if __name__ == '__main__':
    from pymodaq.utils.data import DataWithAxes, DataRaw, Axis
    shape = (4, 10, 5, 7)
    dat = np.arange(np.prod(shape))
    dat = dat.reshape(shape)
    data = DataRaw('mydata', data=[dat], nav_indexes=(0, 1, 2),
                   axes=[Axis(f'axis_{ind:02d}',
                              data=np.linspace(0, shape[ind]-1, shape[ind]),
                              index=ind) for ind in range(len(shape))])
    subdata_sig = data.inav[2, 2, 3].data
    subdata_nav = data.isig[3].data
    data.isig[:]
    pass
