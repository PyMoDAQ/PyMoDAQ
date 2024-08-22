
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


class TestDataFromPlugins:
    def test_attributes(self):
        dwa = data_mod.DataFromPlugins(name='blabla', data=[DATA1D])

        assert hasattr(dwa, 'do_plot')
        assert dwa.do_plot == True

        assert hasattr(dwa, 'do_save')
        assert dwa.do_save == True


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

