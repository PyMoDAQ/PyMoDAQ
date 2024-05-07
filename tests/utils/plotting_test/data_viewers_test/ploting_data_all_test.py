# -*- coding: utf-8 -*-
"""
Created on Thu Feb 29 16:12:05 2024

@author: weber
"""
import pytest

import numpy as np
import tempfile
from pathlib import Path
from itertools import permutations

from pymodaq.utils import math_utils as mutils
from pymodaq.utils import data as datamod
from pymodaq.utils.h5modules.saving import H5SaverLowLevel
from pymodaq.utils.h5modules.data_saving import DataSaverLoader, DataEnlargeableSaver
from pymodaq.utils.plotting.data_viewers import Viewer1D, ViewerND, Viewer2D


@pytest.fixture(scope="module")
def get_3D_array():
    # import tempfile
    # from pathlib import Path
    # import zipfile
    # from urllib.request import urlretrieve
    # import nibabel
    #
    # # Create a temporary directory
    # with tempfile.TemporaryDirectory() as directory_name:
    #     directory = Path(directory_name)
    #     # Define URL
    #     url = 'http://www.fil.ion.ucl.ac.uk/spm/download/data/attention/attention.zip'
    #
    #     # Retrieve the data
    #     fn, info = urlretrieve(url, directory.joinpath('attention.zip'))
    #
    #     # Extract the contents into the temporary directory we created earlier
    #     zipfile.ZipFile(fn).extractall(path=directory)
    #
    #     # Read the image
    #     struct = nibabel.load(directory.joinpath('attention/structural/nsM00587_0002.hdr'))
    #
    #     # Get a plain NumPy array, without all the metadata
    #     array_3D = struct.get_fdata()
    p = Path(__file__).parent.parent.parent
    array_3D = np.load(p.joinpath('data/my_brain.npy'))

    return array_3D

@pytest.fixture(scope='module')
def get_4D():
    x = mutils.linspace_step(-10, 10, 0.2)
    y = mutils.linspace_step(-30, 30, 2)
    t = mutils.linspace_step(-200, 200, 2)
    z = mutils.linspace_step(-50, 50, 0.5)
    data = np.zeros((len(y), len(x), len(t), len(z)))
    amp = np.ones((len(y), len(x), len(t), len(z)))
    for indx in range(len(x)):
        for indy in range(len(y)):
            data[indy, indx, :, :] = amp[indy, indx] * (
                    mutils.gauss2D(z, -50 + indx * 1, 20,
                                   t, 0 + 2 * indy, 30)
                    + np.random.rand(len(t), len(z)) / 10)

    dwa = \
        datamod.DataRaw('NDdata', data=data, dim='DataND',
                        axes=[datamod.Axis(data=y, index=0, label='y_axis', units='yunits'),
                              datamod.Axis(data=x, index=1, label='x_axis', units='xunits'),
                              datamod.Axis(data=t, index=2, label='t_axis', units='tunits'),
                              datamod.Axis(data=z, index=3, label='z_axis', units='zunits')])

    return dwa

@pytest.fixture()
def get_h5saver(tmp_path):
    h5saver = H5SaverLowLevel()
    addhoc_file_path = tmp_path.joinpath('h5file.h5')
    h5saver.init_file(file_name=addhoc_file_path)

    yield h5saver
    h5saver.close_file()

class Test1DPlot:
    def test_plot_0D_1D_uniform(self, qtbot):
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

        viewer = dwa_1D.plot('qt')
        assert isinstance(viewer, Viewer1D)

        with tempfile.TemporaryDirectory() as d:
            with DataSaverLoader(Path(d).joinpath('mydatafile.h5')) as saver_loader:
                saver_loader.add_data('/RawData', dwa_1D)

                dwa_back = saver_loader.load_data('/RawData/Data00', load_all=True)

                assert dwa_back == dwa_1D

    def test_plot_1D_0D_uniform(self, qtbot):
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

        viewer = dwa_1D.plot('qt')
        assert isinstance(viewer, Viewer1D)
        with tempfile.TemporaryDirectory() as d:
            with DataSaverLoader(Path(d).joinpath('mydatafile.h5')) as saver_loader:
                saver_loader.add_data('/RawData', dwa_1D)
                dwa_back = saver_loader.load_data('/RawData/Data00', load_all=True)
                assert dwa_back == dwa_1D


    def test_plot_1D_0D_spread(self, qtbot):

        NX = 100
        axis_spread_array = np.linspace(-20, 50, NX)
        np.random.shuffle(axis_spread_array)
        data_array_1D_spread = mutils.gauss1D(axis_spread_array, 20, 5)

        axis_name = 'axis spread'
        axis_units = 'spread units'

        axis_spread = datamod.Axis(axis_name, axis_units, data=axis_spread_array)

        with tempfile.TemporaryDirectory() as d:
            with DataEnlargeableSaver(Path(d).joinpath('mydatafile.h5'),
                                      enl_axis_names=[axis_name],
                                      enl_axis_units=[axis_units]) as saver_loader:
                for ind in range(NX):
                    data0D = datamod.DataRaw('data0D',
                                             data=[np.array([float(data_array_1D_spread[ind])])],
                                             distribution='uniform',)
                    saver_loader.add_data('/RawData', data0D,
                                          axis_values=[float(axis_spread_array[ind])])

                data1D_spread = saver_loader.load_data('/RawData/EnlData00', load_all=True)
                assert data1D_spread.get_axis_from_index(0)[0] == axis_spread
                print(data1D_spread)
                assert data1D_spread.distribution.name == 'spread'
                assert data1D_spread.dim.name == 'DataND'
                assert data1D_spread.shape == (NX,)

                assert data1D_spread.inav[-1] == data0D

                viewer = data1D_spread.plot('qt')
                assert isinstance(viewer, Viewer1D)

    def test_plot_0D_1D_spread(self, qtbot, get_h5saver):
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
        viewer = dwa_back.plot('qt')
        assert isinstance(viewer, ViewerND)

class Test2DPlot:
    def test_plot_0D_2D_uniform(self, qtbot):
        NX = 100
        NY = 50

        x_axis = datamod.Axis('xaxis', 'xunits', data=np.linspace(-20, 50, NX), index=1)
        y_axis = datamod.Axis('yaxis', 'yunits', data=np.linspace(20, 40, NY), index=0)
        data_array_2D = mutils.gauss2D(x_axis.get_data(), 0, 5, y_axis.get_data(), 30, 5)

        data2D = datamod.DataRaw('data2DUniform', data=[data_array_2D],
                                 axes=[x_axis, y_axis])
        print(data2D)
        assert data2D.distribution == 'uniform'
        assert data2D.dim == 'Data2D'
        viewer = data2D.plot('qt')
        assert isinstance(viewer, Viewer2D)

    @pytest.mark.parametrize('nav_index', (0, 1))
    def test_plot_1D_1D_uniform(self, qtbot, nav_index):
        NX = 100
        NY = 50

        x_axis = datamod.Axis('xaxis', 'xunits', data=np.linspace(-20, 50, NX), index=1)
        y_axis = datamod.Axis('yaxis', 'yunits', data=np.linspace(20, 40, NY), index=0)
        data_array_2D = mutils.gauss2D(x_axis.get_data(), 0, 5, y_axis.get_data(), 30, 5)

        data2D = datamod.DataRaw('data2DUniform', data=[data_array_2D],
                                 axes=[x_axis, y_axis],
                                 nav_indexes=(nav_index,))
        print(data2D)
        assert data2D.distribution == 'uniform'
        assert data2D.dim == 'DataND'
        viewer = data2D.plot('qt')
        assert isinstance(viewer, Viewer2D)

    def test_plot_2D_0D_uniform(self, qtbot):
        NX = 100
        NY = 50

        x_axis = datamod.Axis('xaxis', 'xunits', data=np.linspace(-20, 50, NX), index=1)
        y_axis = datamod.Axis('yaxis', 'yunits', data=np.linspace(20, 40, NY), index=0)
        data_array_2D = mutils.gauss2D(x_axis.get_data(), 0, 5, y_axis.get_data(), 30, 5)

        data2D = datamod.DataRaw('data2DUniform', data=[data_array_2D],
                                 axes=[x_axis, y_axis],
                                 nav_indexes=(0, 1))
        print(data2D)
        assert data2D.distribution == 'uniform'
        assert data2D.dim == 'DataND'
        viewer = data2D.plot('qt')
        assert isinstance(viewer, Viewer2D)

    def test_plot_2D_0D_spread(self, qtbot):
        N = 100
        x_axis_array = np.random.randint(-20, 50, size=N)
        y_axis_array = np.random.randint(20, 40, size=N)
        x_axis = datamod.Axis('xaxis', 'xunits', data=x_axis_array, index=0, spread_order=0)
        y_axis = datamod.Axis('yaxis', 'yunits', data=y_axis_array, index=0, spread_order=1)

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
        assert data2D_spread.distribution == 'spread'
        assert data2D_spread.dim == 'DataND'

        viewer = data2D_spread.plot('qt')
        assert isinstance(viewer, Viewer2D)

    def test_plot_1D_1D_spread(self, qtbot):
        N = 10
        axis_array = np.linspace(0, 2*np.pi, N)
        axis = datamod.Axis('axis', 'units', data=axis_array, index=0, spread_order=0)

        NX = 100
        x_axis = datamod.Axis('xaxis', 'xunits', data=np.linspace(-20, 50, NX), index=1)
        data_array_1D = mutils.gauss1D(x_axis.get_data(), 10, 5)

        data_list = []
        for ind in range(N):
            data_list.append(data_array_1D * np.sin(axis_array[ind]))

        data_array = datamod.squeeze(np.array(data_list))
        assert data_array.shape == (N, NX)

        data2D_spread = datamod.DataRaw('data2DSpread', data=[data_array],
                                        axes=[axis, x_axis],
                                        distribution='spread',
                                        nav_indexes=(0,))
        print(data2D_spread)
        assert data2D_spread.distribution == 'spread'
        assert data2D_spread.dim == 'DataND'

        viewer = data2D_spread.plot('qt')
        assert isinstance(viewer, ViewerND)

class Test3DPlot:
    @pytest.mark.parametrize('nav_index', ((0,), (1,), (2,), (0, 1), (0, 2), (1, 2)))
    def test_plot_0D_3D_uniform(self, qtbot, get_3D_array, nav_index):

        data3D = datamod.DataRaw('data3DUniform', data=[get_3D_array],
                                 nav_indexes=nav_index,
                                 )
        data3D.create_missing_axes()

        print(data3D)
        assert data3D.distribution == 'uniform'
        assert data3D.dim == 'DataND'
        viewer = data3D.plot('qt')
        assert isinstance(viewer, ViewerND)

class Test4DPlot:
    @pytest.mark.parametrize('nav_indexes',
                             list(permutations((0, 1, 2, 3), 2))[:4] +
                             list(permutations((0, 1, 2, 3), 3))[:3] +
                             [(0, 1, 2, 3)])
    def test_plot_4D_uniform(self, qtbot, get_4D, nav_indexes):
        dwa = get_4D
        dwa.nav_indexes = nav_indexes
        print(dwa)
        assert dwa.distribution == 'uniform'
        assert dwa.dim == 'DataND'
        viewer = dwa.plot('qt')
        assert isinstance(viewer, ViewerND)

    def test_plot_4D_spread(self, qtbot):
        N = 100

        x = np.sin(np.linspace(0, 4 * np.pi, N))
        y = np.sin(np.linspace(0, 4 * np.pi, N) + np.pi / 6)
        z = np.sin(np.linspace(0, 4 * np.pi, N) + np.pi / 3)

        Nsig = 200
        axis = datamod.Axis('signal axis', 'signal units', data=np.linspace(-10, 10, Nsig), index=1)
        data = np.zeros((N, Nsig))
        for ind in range(N):
            data[ind, :] = mutils.gauss1D(axis.get_data(),
                                          np.sqrt(x[ind] ** 2 + y[ind] ** 2 + z[ind] ** 2),
                                          2) + np.random.rand(Nsig)

        dwa = datamod.DataRaw('NDdata', data=data, distribution='spread', dim='DataND',
                              nav_indexes=(0,),
                              axes=[datamod.Axis(data=x, index=0, label='x_axis', units='xunits',
                                                 spread_order=0),
                                    datamod.Axis(data=y, index=0, label='y_axis', units='yunits',
                                                 spread_order=0),
                                    datamod.Axis(data=z, index=0, label='z_axis', units='zunits',
                                                 spread_order=0),
                                    axis
                                    ])

        viewer = dwa.plot('qt')
        assert isinstance(viewer, ViewerND)
