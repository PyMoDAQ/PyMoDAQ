import numpy as np
import pytest

import pymodaq.daq_utils
from pymodaq.daq_utils import scanner

class TestScans:

    def test_ScanInfo(self):
        Nsteps = 10
        axes_indexes = []
        axes_unique = []
        positions = []
        scan_param = scanner.ScanInfo(Nsteps, positions, axes_indexes, axes_unique)
        assert scan_param.Nsteps is Nsteps
        assert scan_param.axes_indexes is axes_indexes
        assert scan_param.axes_unique is axes_unique
        assert scan_param.positions is positions


    def test_set_scan_spiral(self):

        nsteps = 10
        starts = np.array([10.1, -5.87])
        steps = np.array([0.12, 1])
        rmaxs = np.rint(nsteps / 2) * steps


        positions = scanner.set_scan_spiral(starts, rmaxs, steps, nsteps=None)

        positions2 = scanner.set_scan_spiral(starts, [], steps, nsteps=nsteps)
        assert isinstance(positions, np.ndarray)
        assert positions.shape == (121, 2)
        assert np.all(positions == pytest.approx(positions2))

        positions = scanner.set_scan_spiral(starts, np.rint(10000 / 2) * steps, steps)
        assert positions.shape[0] == 16384


    def test_set_scan_linear(self):

        positions = scanner.set_scan_linear(np.array([0, 0]), np.array([1, -21]), np.array([0.1, -0.3]))

        assert positions.shape == (781, 2)

        positions = scanner.set_scan_linear(np.array([0, 0]), np.array([1, -21]), np.array([0.01, -0.03]))
        assert positions.shape == (10032, 2)
        positions = scanner.set_scan_linear(np.array([0, 0]), np.array([1, -21]),
                                                           np.array([0.01, -0.03]), False, 1000)
        assert positions.shape == (1092, 2)

        #  test back and forth
        positionsbf = scanner.set_scan_linear(np.array([0, 0]), np.array([1, 21]), np.array([0.1, 0.3]), True, 1000)
        assert positionsbf.shape == (781, 2)
        nx = len(np.unique(positionsbf[:, 0]))
        ny = len(np.unique(positionsbf[:, 1]))
        assert np.all(positionsbf[:ny-1, 1] ==
                      positionsbf[2*ny-1:ny:-1, 1])

        positions = scanner.set_scan_linear(np.array([0, 0]), np.array([1, 21]), np.array([0., 0.3]))
        assert positions.shape == (1, 2)
        positions = scanner.set_scan_linear(np.array([0, 0]), np.array([1, -21]), np.array([0.1, 0.3]))
        assert positions.shape == (1, 2)
        positions = scanner.set_scan_linear(np.array([0, 0]), np.array([0, 21]), np.array([0.1, 0.3]))
        assert positions.shape == (1, 2)

    def test_set_scan_random(self):
        positions = scanner.set_scan_linear(np.array([0, 0]), np.array([1, -21]), np.array([0.1, -0.3]))
        positions_r = scanner.set_scan_random(np.array([0, 0]), np.array([1, -21]), np.array([0.1, -0.3]))

        assert positions_r.shape == positions.shape
        for pos in positions_r:
            assert pos in positions
