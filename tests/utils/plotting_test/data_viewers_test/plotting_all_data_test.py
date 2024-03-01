# -*- coding: utf-8 -*-
"""
Created on Thu Feb 29 16:12:05 2024

@author: weber
"""
import pytest

import numpy as np
import tempfile
from pathlib import Path

from pymodaq.utils import math_utils as mutils
from pymodaq.utils import data as datamod
from pymodaq.utils.h5modules.saving import H5SaverLowLevel
from pymodaq.utils.h5modules.data_saving import DataSaverLoader, DataEnlargeableSaver


@pytest.fixture()
def get_h5saver(tmp_path):
    h5saver = H5SaverLowLevel()
    addhoc_file_path = tmp_path.joinpath('h5file.h5')
    h5saver.init_file(file_name=addhoc_file_path)

    yield h5saver
    h5saver.close_file()


def test_plot_0D_1D_uniform(qtbot):
    #%%
    NX = 100
    x_axis = datamod.Axis('xaxis', 'xunits', data=np.linspace(-20, 50, NX), index=0)
    data_array_1D = mutils.gauss1D(x_axis.get_data(), 10, 5)

    dwa_1D = datamod.DataRaw('data1DUniform', data=[data_array_1D, -data_array_1D],
                             axes=[x_axis])
    print(dwa_1D)
    assert dwa_1D.distribution.name == 'uniform'
    assert dwa_1D.dim.name == 'Data1D'
    assert dwa_1D.shape == (NX,)

    dwa_1D.plot('qt')

    with tempfile.TemporaryDirectory() as d:
        with DataSaverLoader(Path(d).joinpath('mydatafile.h5')) as saver_loader:
            saver_loader.add_data('/RawData', dwa_1D)

            dwa_back = saver_loader.load_data('/RawData/Data00', load_all=True)

            assert dwa_back == dwa_1D

def test_plot_1D_0D_uniform(qtbot):
    #%%
    NX = 100
    x_axis = datamod.Axis('xaxis', 'xunits', data=np.linspace(-20, 50, NX), index=0)
    data_array_1D = mutils.gauss1D(x_axis.get_data(), 10, 5)

    dwa_1D = datamod.DataRaw('data1DUniform', data=[data_array_1D, -data_array_1D],
                             axes=[x_axis],
                             nav_indexes=(0,))
    print(dwa_1D)
    assert dwa_1D.distribution.name == 'uniform'
    assert dwa_1D.dim.name == 'DataND'
    assert dwa_1D.shape == (NX,)

    dwa_1D.plot('qt')

    with tempfile.TemporaryDirectory() as d:
        with DataSaverLoader(Path(d).joinpath('mydatafile.h5')) as saver_loader:
            saver_loader.add_data('/RawData', dwa_1D)
            dwa_back = saver_loader.load_data('/RawData/Data00', load_all=True)
            assert dwa_back == dwa_1D


def test_plot_1D_0D_spread(qtbot):

    NX = 100
    axis_spread_array = np.linspace(-20, 50, NX)
    np.random.shuffle(axis_spread_array)
    data_array_1D_spread = mutils.gauss1D(axis_spread_array, 20, 5)

    axis_spread = datamod.Axis('axis spread', 'units', data=axis_spread_array)

    data1D_spread = datamod.DataRaw('data1DSpread', data=[data_array_1D_spread],
                                    distribution='spread',
                                    nav_indexes=(0,),
                                    axes=[axis_spread])
    print(data1D_spread)
    assert data1D_spread.distribution.name == 'spread'
    assert data1D_spread.dim.name == 'DataND'
    assert data1D_spread.shape == (NX,)
    data1D_spread.plot('qt')

    with tempfile.TemporaryDirectory() as d:
        with DataSaverLoader(Path(d).joinpath('mydatafile.h5')) as saver_loader:
            saver_loader.add_data('/RawData', data1D_spread)

            dwa_back = saver_loader.load_data('/RawData/Data00', load_all=True)

            assert dwa_back == data1D_spread

def test_plot_0D_1D_spread(qtbot, get_h5saver):
    # when loading data from an enlarged array with a nav axis of size 0, there is an extra dimension
    #in the array of len 1: shape = (1, N) simulated here by using expand_dims
    h5saver = get_h5saver
    data_saver = DataEnlargeableSaver(h5saver)
    NX = 100
    axis_array = np.linspace(-20, 50, NX)
    data_array_1D = mutils.gauss1D(axis_array, 20, 5)
    axis_sig = datamod.Axis('axis spread', 'units', data=axis_array, index=0)
    data_to_append = datamod.DataRaw('data1D', data=[data_array_1D],
                                     axes=[axis_sig])

    axis_value = 12.

    data_saver.add_data('/RawData', data_to_append, axis_values=[axis_value])

    dwa_back = data_saver.load_data('/RawData/EnlData00', load_all=True)
    assert dwa_back.inav[0] == data_to_append
    dwa_back.plot('qt')

    data_saver.add_data('/RawData', data_to_append, axis_values=[axis_value+1])
    dwa_back = data_saver.load_data('/RawData/EnlData00', load_all=True)
    assert dwa_back.inav[1] == data_to_append
    dwa_back.plot('qt')

    data_saver.add_data('/RawData', data_to_append, axis_values=[axis_value + 2])
    dwa_back = data_saver.load_data('/RawData/EnlData00', load_all=True)
    assert dwa_back.inav[2] == data_to_append
    dwa_back.plot('qt')


if __name__ == '__main__':
    from qtpy import QtWidgets
    import sys
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        h5saver = H5SaverLowLevel()
        h5saver.init_file(file_name=Path(d).joinpath('myh5.h5'))

        app = QtWidgets.QApplication(sys.argv)
        test_plot_0D_1D_spread(None, h5saver)

        h5saver.close_file()

    sys.exit(app.exec_())