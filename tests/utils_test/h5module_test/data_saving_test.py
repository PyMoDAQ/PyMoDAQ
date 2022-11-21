# -*- coding: utf-8 -*-
"""
Created the 21/11/2022

@author: Sebastien Weber
"""
import numpy as np
import pytest

from pymodaq.utils.h5modules import saving
from pymodaq.utils.h5modules.data_saving import Saver, AxisSaverLoader
from pymodaq.utils.data import Axis


@pytest.fixture()
def get_h5saver(tmp_path):
    h5saver = saving.H5SaverLowLevel()
    addhoc_file_path = tmp_path.joinpath('h5file.h5')
    h5saver.init_file(file_name=addhoc_file_path, file_type=saving.FileType['detector'])

    yield h5saver
    h5saver.close_file()


class TestAxisSaverLoader:

    def test_init(self, get_h5saver):
        h5saver = get_h5saver
        axis_saver = AxisSaverLoader(h5saver)
        assert axis_saver.data_type.name == 'axis'

    def test_add_axis(self, get_h5saver):
        h5saver = get_h5saver
        axis_saver = AxisSaverLoader(h5saver)
        SIZE = 10
        OFFSET = -5.
        SCALING = 0.2
        INDEX = 5
        LABEL = 'myaxis'
        UNITS = 'myunits'
        axis = Axis(label=LABEL, units=UNITS, data=OFFSET + SCALING * np.linspace(0, SIZE-1, SIZE), index=INDEX)

        axis_node = axis_saver.add_axis(h5saver._raw_group, axis)

        attrs = ['label', 'units', 'offset', 'scaling', 'index']
        attrs_values = [LABEL, UNITS, OFFSET, SCALING, INDEX]
        for ind, attr in enumerate(attrs):
            assert attr in axis_node.attrs
            if isinstance(attrs_values[ind], float):
                assert axis_node.attrs[attr] == pytest.approx(attrs_values[ind])
            else:
                assert axis_node.attrs[attr] == attrs_values[ind]
        assert axis_node.read() == pytest.approx(axis.data)

    def test_load_axis(self, get_h5saver):
        h5saver = get_h5saver
        axis_saver = AxisSaverLoader(h5saver)
        SIZE = 10
        OFFSET = -5.
        SCALING = 0.2
        INDEX = 5
        LABEL = 'myaxis'
        UNITS = 'myunits'
        axis = Axis(label=LABEL, units=UNITS, data=OFFSET + SCALING * np.linspace(0, SIZE - 1, SIZE), index=INDEX)

        axis_node = axis_saver.add_axis(h5saver._raw_group, axis)

        axis_back = axis_saver.load_axis(axis_node)
        assert isinstance(axis_back, Axis)
        assert axis_back == axis