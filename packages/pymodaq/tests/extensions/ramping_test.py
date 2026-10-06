import numpy as np
import pytest

from pymodaq_data import Q_

from pymodaq.extensions.ramping.utilities.ramp_generator import RampGenerator
from pymodaq.extensions.ramping.utilities.histograming import HistogramProcessor


class TestRampGenerator:
    def test_linear(self):
        ramp = RampGenerator(Q_(0., 'mm'), Q_(10., 'mm'), Q_(4., 's'))
        assert ramp(Q_(0., 's')) == Q_(0., 'mm')
        assert ramp(Q_(1., 's')) == Q_(2.5, 'mm')
        assert ramp(Q_(4., 's')) == Q_(10., 'mm')

    def test_ramp_down(self):
        ramp = RampGenerator(Q_(10., 'K'), Q_(5., 'K'), Q_(1., 'min'))
        assert ramp(Q_(30., 's')).m_as('K') == pytest.approx(7.5)

    def test_clamped(self):
        ramp = RampGenerator(Q_(0., 'mm'), Q_(10., 'mm'), Q_(4., 's'))
        assert ramp(Q_(-1., 's')) == Q_(0., 'mm')
        assert ramp(Q_(10., 's')) == Q_(10., 'mm')

    def test_zero_duration(self):
        ramp = RampGenerator(Q_(0., 'mm'), Q_(10., 'mm'), Q_(0., 's'))
        assert ramp(Q_(1., 's')) == Q_(10., 'mm')


def test_average_data_over_indexes():
    data = np.array([1., 3., 10., 20., 5.])
    indexes = np.array([0, 0, 1, 1, 2])
    assert np.allclose(HistogramProcessor.average_data_over_indexes(data, indexes), [2., 15., 5.])
