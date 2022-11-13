# -*- coding: utf-8 -*-
"""
Created the 07/11/2022

@author: Sebastien Weber
"""
import numpy as np


class SpecialSlicers(object):
    """make it elegant to apply a slice to navigation or signal dimensions"""
    def __init__(self, obj, is_navigation):
        self.is_navigation = is_navigation
        self.obj = obj

    def __getitem__(self, slices):
        return self.obj._slicer(slices, self.is_navigation)


class SpecialSlicersData(SpecialSlicers):

    def __setitem__(self, i, j):
        """x.__setitem__(i, y) <==> x[i]=y
        """
        raise NotImplementedError
        if hasattr(j, 'data'):
            j = j.data
        array_slices = self.obj._get_array_slices(i, self.is_navigation)
        self.obj.data[array_slices] = j

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
