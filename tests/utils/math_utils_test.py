# -*- coding: utf-8 -*-
"""
Created the 08/03/2022

@author: Sebastien Weber
"""
import pytest
import numpy as np

from pymodaq.utils import units
from pymodaq.utils import math_utils as mutils
from pymodaq.utils import daq_utils as utils


class TestMath:
    def test_my_moment(self):
        x = mutils.linspace_step(0, 100, 1)
        y = mutils.gauss1D(x, 42.321,
                          13.5)  # relation between dx in the gauss1D and in the moment is np.sqrt(4*np.log(2))

        x0, dx = mutils.my_moment(x, y)
        assert x0 == pytest.approx(42.321)
        assert dx * np.sqrt(4 * np.log(2)) == pytest.approx(13.5)

    def test_normalize(self):
        x = mutils.linspace_step(0, 100, 1)
        ind = np.random.randint(1, 100 + 1)
        assert mutils.normalize(x)[ind] == \
               pytest.approx(mutils.linspace_step(0, 1, 0.01)[ind])

    def test_odd_even(self):
        assert not mutils.odd_even(10)
        assert mutils.odd_even(-11)

        with pytest.raises(TypeError):
            assert mutils.odd_even(11.2)

    def test_greater2n(self):
        assert mutils.greater2n(127) == 128
        assert mutils.greater2n(62.95) == 64

        with pytest.raises(TypeError):
            assert mutils.greater2n(True)
        with pytest.raises(TypeError):
            assert mutils.greater2n([10.4, 248, True])
        with pytest.raises(TypeError):
            assert mutils.greater2n([45, 72.4, "51"])
        with pytest.raises(TypeError):
            assert mutils.greater2n(1j)

        assert mutils.greater2n([10.4, 248, 1020]) == [16, 256, 1024]
        assert np.all(mutils.greater2n(np.array([10.4, 248, 1020])) == np.array([16, 256, 1024]))

    def test_linspace_step(self):
        assert np.all(mutils.linspace_step(-1.0, 10, 1) == np.array([-1., 0., 1., 2., 3., 4., 5., 6., 7., 8., 9., 10.]))
        assert np.all(
            mutils.linspace_step(1.0, -1, -0.13) == pytest.approx(
                np.array([1., 0.87, 0.74, 0.61, 0.48, 0.35, 0.22, 0.09, -0.04,
                          -0.17, -0.3, -0.43, -0.56, -0.69, -0.82, -0.95])))
        with pytest.raises(ValueError):
            mutils.linspace_step(45, 45, 1)
        with pytest.raises(ValueError):
            mutils.linspace_step(0, 10, -1)
        with pytest.raises(ValueError):
            mutils.linspace_step(0, 10, 0.)

    def test_linspace_step_N(self):
        START = -1.
        STEP = 0.25
        LENGTH = 5
        data = mutils.linspace_step_N(START, STEP, LENGTH)
        assert len(data) == LENGTH
        assert np.any(data == pytest.approx(np.array([-1, -0.75, -0.5, -0.25, -0.])))

    def test_find_index(self):  # get closest value and index
        x = mutils.linspace_step(1.0, -1, -0.13)
        assert mutils.find_index(x, -0.55) == [(12, -0.56)]
        assert mutils.find_index(x, [-0.55, 0.741]) == [(12, -0.56), (2, 0.74)]
        assert mutils.find_index(x, 10) == [(0, 1.)]

    def test_find_common_index(self):
        IND_TEST = np.random.randint(0, 99, 1)[0]
        x = np.random.random(100)
        y = np.random.rand(100)
        x0 = x[IND_TEST]
        y0 = y[IND_TEST]
        ind, x_val, y_val = mutils.find_common_index(x, y, x0, y0)
        assert ind == IND_TEST and x_val == pytest.approx(x[IND_TEST])\
               and y_val == pytest.approx(y[IND_TEST])

    def test_gauss1D(self):
        x = mutils.linspace_step(1.0, -1, -0.13)
        x0 = -0.55
        dx = 0.1
        n = 1
        assert np.all(mutils.gauss1D(x, x0, dx, n) == pytest.approx(
            np.exp(-2 * np.log(2) ** (1 / n) * ((x - x0) / dx) ** (2 * n))))
        with pytest.raises(ValueError):
            mutils.gauss1D(x, x0, -0., 1)
        with pytest.raises(TypeError):
            mutils.gauss1D(x, x0, 0.1, 1.1)
        with pytest.raises(ValueError):
            mutils.gauss1D(x, x0, 0.1, -1)

    def test_gauss2D(self):
        x = mutils.linspace_step(-1.0, 1, 0.1)
        x0 = -0.55
        dx = 0.1
        y = mutils.linspace_step(-2.0, -1, 0.1)
        y0 = -1.55
        dy = 0.2
        n = 1
        assert np.all(mutils.gauss2D(x, x0, dx, y, y0, dy, n) == pytest.approx(
            np.transpose(np.outer(mutils.gauss1D(x, x0, dx, n), mutils.gauss1D(y, y0, dy, n)))))
        assert np.all(
            mutils.gauss2D(x, x0, dx, y, y0, dy, n) == pytest.approx(mutils.gauss2D(x, x0, dx, y, y0, dy, n, 180)))
        assert np.all(
            mutils.gauss2D(x, x0, dx, y, y0, dy, n, -90) == pytest.approx(mutils.gauss2D(x, x0, dx, y, y0, dy, n, 90)))
        assert np.all(
            mutils.gauss2D(x, x0, dx, y, y0, dy, n) == pytest.approx(mutils.gauss2D(x, x0, dy, y, y0, dx, n, 90)))

    def test_ftAxis(self):
        omega_max = units.l2w(800)
        Npts = 1024
        omega_grid, time_grid = mutils.ftAxis(Npts, omega_max)
        assert len(omega_grid) == Npts
        assert len(time_grid) == Npts
        assert np.max(time_grid) == (Npts - 1) * np.pi / (2 * omega_max)

        with pytest.raises(TypeError):
            assert mutils.ftAxis("40", omega_max)
        with pytest.raises(ValueError):
            assert mutils.ftAxis(0, omega_max)

    def test_ftAxis_time(self):
        time_max = 10000  # fs
        Npts = 1024
        omega_grid, time_grid = mutils.ftAxis_time(Npts, time_max)
        assert len(omega_grid) == Npts
        assert len(time_grid) == Npts
        assert np.max(omega_grid) == (Npts - 1) / 2 * 2 * np.pi / time_max

        with pytest.raises(TypeError):
            assert mutils.ftAxis_time("40", time_max)
        with pytest.raises(ValueError):
            assert mutils.ftAxis_time(0, time_max)

    def test_ft(self):
        omega_max = units.l2w(300)
        omega0 = units.l2w(800)
        Npts = 2 ** 10
        omega_grid, time_grid = mutils.ftAxis(Npts, omega_max)
        signal_temp = np.sin(omega0 * time_grid) * mutils.gauss1D(time_grid, 0, 100, 1)
        signal_omega = mutils.ft(signal_temp)

        assert np.abs(omega_grid[np.argmax(np.abs(signal_omega))]) == pytest.approx(omega0, rel=1e-2)
        with pytest.raises(Exception):
            mutils.ft(signal_temp, 2)

        with pytest.raises(TypeError):
            mutils.ft(signal_temp, 1.5)
        with pytest.raises(TypeError):
            mutils.ft(signal_temp, "40")

    def test_ift(self):
        omega_max = units.l2w(300)
        omega0 = units.l2w(800)
        Npts = 2 ** 10
        omega_grid, time_grid = mutils.ftAxis(Npts, omega_max)
        signal_temp = np.sin(omega0 * time_grid) * mutils.gauss1D(time_grid, 0, 100, 1)
        signal_omega = mutils.ft(signal_temp)
        assert np.all(signal_temp == pytest.approx(np.real(mutils.ift(signal_omega))))
        with pytest.raises(Exception):
            mutils.ift(signal_temp, 2)

        with pytest.raises(TypeError):
            mutils.ift(signal_temp, 1.5)
        with pytest.raises(TypeError):
            mutils.ift(signal_temp, "40")

    def test_ft2(self):
        x = np.array([np.linspace(1, 10, 10), np.linspace(10, 1, 10)])

        with pytest.raises(TypeError):
            mutils.ft2(x, dim=(1.1, 1.2))
        with pytest.raises(TypeError):
            mutils.ft2(x, dim=1.1)

    def test_ift2(self):
        x = np.array([np.linspace(1, 10, 10), np.linspace(10, 1, 10)])
        with pytest.raises(TypeError):
            mutils.ift2(x, dim=(1.1, 1.2))
        with pytest.raises(TypeError):
            mutils.ift2(x, dim=1.1)
            
    def test_rotate2D(self):
        accuracy = 10 # Rouding precision
        x,y = (0,0) # Point to rotate
        ox,oy = (1,1) # Origin 
        angle = np.pi/2 # Angle
        x_r,y_r = mutils.rotate2D((ox,oy),(x,y),angle)    
        assert (np.round((x_r,y_r),accuracy) == np.array([2,0])).all()        
        angle = np.pi
        x_r,y_r = mutils.rotate2D((ox,oy),(x,y),angle)    
        assert (np.round((x_r,y_r),accuracy) == np.array([2,2])).all()
        ox,oy = (1,0)
        x_r,y_r = mutils.rotate2D((ox,oy),(x,y),angle)                 
        assert (np.round((x_r,y_r),accuracy) == np.array([2,0])).all()
        ox,oy = (0,1)
        x_r,y_r = mutils.rotate2D((ox,oy),(x,y),angle)                         
        assert (np.round((x_r,y_r),accuracy) == np.array([0,2])).all()
        x,y = (1,1)
        x_r,y_r = mutils.rotate2D((ox,oy),(x,y),angle)                                 
        assert (np.round((x_r,y_r),accuracy) == np.array([-1,1])).all()

