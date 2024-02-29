# -*- coding: utf-8 -*-
"""
Created on Thu Feb 29 16:12:05 2024

@author: weber
"""
import numpy as np


from pymodaq.utils import math_utils as mutils
from pymodaq.utils import data as datamod

from pymodaq.utils.plotting.data_viewers.viewer2D import Viewer2D

#%%
NX = 100
NY = 50

x_axis = datamod.Axis('xaxis', 's', data=np.linspace(-20, 50, NX), index=1)
y_axis = datamod.Axis('yaxis', 's', data=np.linspace(20, 40, NY), index=0)

axis_spread_array = x_axis.get_data()
np.random.shuffle(x_axis.get_data())
y_axis_spread = datamod.Axis('xaxis', 's', data=axis_spread_array)

data_array_1D = mutils.gauss1D(y_axis.get_data(), 30, 5)
data_array_1D_spread = mutils.gauss1D(y_axis_spread.get_data(), 20, 5)
data_array_2D = mutils.gauss2D(x_axis.get_data(), 0, 5, y_axis.get_data(), 30, 5)


class TestData1D:

    def test_1D_uniform(self, qtbot):
        data1D = datamod.DataRaw('data1DUniform', data=[data_array_1D, -data_array_1D],
                                 axes=[y_axis])
        print(data1D)
        print(data1D.distribution)
        print(data1D.dim)
        data1D.plot('qt')

        #%% uniform 1D nav
        data1D.nav_indexes = (0,)
        print(data1D)
        print(data1D.distribution)
        print(data1D.dim)
        data1D.plot('qt')

    def test_1D_spread(self, qtbot):
        #%% spread 1D signal => forced to be plotted on 1Dviewer like if it was uniform

        data1D_spread = datamod.DataRaw('data1DSpread', data=[data_array_1D_spread],
                                        distribution='spread',
                                        axes=[y_axis_spread])
        print(data1D_spread)
        print(data1D_spread.distribution)
        print(data1D_spread.dim)
        data1D_spread.plot('qt')

        #%% spread 1D navigation
        data_array_1D_spread_exp = np.expand_dims(data_array_1D_spread, axis=-1)
        data1D_spread_nav = datamod.DataRaw('data1DSpread', data=[data_array_1D_spread_exp],
                                        distribution='spread',
                                        axes=[y_axis_spread],
                                        nav_indexes = (0, ))

        print(data1D_spread_nav)
        print(data1D_spread_nav.distribution)
        data1D_spread_nav.plot('qt')


class TestData2D:
    def test_2D_spread(self, qtbot):
        N = 100
        x_axis_array = np.random.randint(-20, 50, size=N)
        y_axis_array = np.random.randint(20, 40, size=N)
        x_axis = datamod.Axis('xaxis', 's', data=x_axis_array, index=0, spread_order=0)
        y_axis = datamod.Axis('yaxis', 's', data=y_axis_array, index=0, spread_order=1)

        data_list = []
        for ind in range(N):
            data_list.append(mutils.gauss2D(x_axis.get_data()[ind], 0, 5,
                                            y_axis.get_data()[ind], 30, 5))
        data_array = datamod.squeeze(np.array(data_list))
        data_array.shape

        data2D_spread = datamod.DataRaw('data2DSpread', data=[data_array],
                                 axes=[x_axis, y_axis],
                                 distribution='spread',
                                 nav_indexes=(0,))
        print(data2D_spread)
        print(data2D_spread.shape)
        print(data2D_spread.distribution)
        print(data2D_spread.dim)

        viewer = Viewer2D()
        viewer.show_data(data2D_spread)

        pass
