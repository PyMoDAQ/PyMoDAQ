
"""
Created the 28/10/2022

@author: Sebastien Weber
"""

import numpy as np
import pytest

from pymodaq.utils import data as data_mod
from pymodaq.utils.data import DataDim


LABEL = 'A Label'
UNITS = 'units'
OFFSET = -20.4
SCALING = 0.22
SIZE = 20
DATA = OFFSET + SCALING * np.linspace(0, SIZE-1, SIZE)

DATA0D = np.array([2.7])
DATA1D = np.arange(0, 10)
DATA2D = np.arange(0, 5*6).reshape((5, 6))
DATAND = np.arange(0, 5 * 6 * 3).reshape((5, 6, 3))
Nn0 = 10
Nn1 = 5


def init_axis(data=None, index=0) -> data_mod.Axis:
    if data is None:
        data = DATA
    return data_mod.Axis(label=LABEL, units=UNITS, data=data, index=index)


def init_data(data=None, Ndata=1, axes=[], name='myData', source=data_mod.DataSource['raw'],
              labels=None, units='') -> data_mod.DataWithAxes:
    if data is None:
        data = DATA2D
    return data_mod.DataWithAxes(name, units=units, source=source,
                                 data=[data for ind in range(Ndata)],
                                 axes=axes, labels=labels)


class TestDataSource:
    def test_data_from_plugins(self):
        Ndata = 2
        data = data_mod.DataFromPlugins('myData', data=[DATA2D for ind in range(Ndata)])
        assert isinstance(data, data_mod.DataWithAxes)
        assert data.source == data_mod.DataSource['raw']


class TestDataFromPlugins:
    def test_attributes(self):
        dwa = data_mod.DataFromPlugins(name='blabla', data=[DATA1D])

        assert hasattr(dwa, 'do_plot')
        assert dwa.do_plot is True

        assert hasattr(dwa, 'do_save')
        assert dwa.do_save is True



class TestDataActuator:
    def test_init(self):
        Ndata = 2
        data = data_mod.DataActuator('myact')
        assert data.name == 'myact'
        assert data.data[0] == pytest.approx(0.)

        data = data_mod.DataActuator()
        assert data.name == 'actuator'
        assert data.dim == DataDim['Data0D']
        assert data.length == 1
        assert data.size == 1

        assert data.shape == (1, )
        assert data.data[0] == pytest.approx(0.)

    @pytest.mark.parametrize("data_number", [23, 0.25, -0.7, 1j*12])
    def test_quick_format(self, data_number):
        d = data_mod.DataActuator(data=data_number)
        assert d.name == 'actuator'
        assert d.data[0] == np.array([data_number])

    @pytest.mark.parametrize('datatmp', (DATA0D, DATA1D, DATA2D))
    def test_comparison_data_actuator(self, datatmp):
        LENGTH = 3
        data = init_data(datatmp, LENGTH)
        data_eq = init_data(datatmp, LENGTH)
        data_lt = init_data(datatmp - 0.01 * np.ones(datatmp.shape), LENGTH)
        data_gt = init_data(datatmp + 0.01 * np.ones(datatmp.shape), LENGTH)

        assert data == data_eq
        assert data >= data_eq
        assert data <= data_eq
        assert data > data_lt
        assert data < data_gt

    def test_comparison_numbers(self):
        LENGTH = 1
        data = init_data(DATA0D, LENGTH)
        data_eq = float(DATA0D[0])
        data_lt = float(DATA0D[0]) - 0.01
        data_gt = float(DATA0D[0]) + 0.01

        assert data == data_eq
        assert data >= data_eq
        assert data <= data_eq
        assert data > data_lt
        assert data < data_gt

        ARRAY = np.array([1, 2, 1.5])
        data = data_mod.DataActuator(data=[ARRAY])
        assert not data > 1
        assert data > 0.999
        assert data >= 1
        assert data == data_mod.DataActuator(data=[ARRAY])
        assert data < 2.001
        assert data <= 2
