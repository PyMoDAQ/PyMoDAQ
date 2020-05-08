import numpy as np
import pytest

import pymodaq.daq_utils


class TestScans:

    def test_ScanParameters(self):
        Nsteps = 10
        axis_1_indexes = []
        axis_2_indexes = []
        axis_1_unique = []
        axis_2_unique = [],
        positions = []
        scan_param = pymodaq.daq_utils.scanner.ScanParameters(Nsteps, axis_1_indexes, axis_2_indexes,
                                                              axis_1_unique, axis_2_unique, positions)
        assert scan_param.Nsteps is Nsteps
        assert axis_1_indexes is axis_1_indexes
        assert axis_2_indexes is axis_2_indexes
        assert axis_1_unique is axis_1_unique
        assert axis_2_unique is axis_2_unique

    def test_set_scan_spiral(self):
        sparam = pymodaq.daq_utils.scanner.set_scan_spiral(10.1, -5.87, 0.5, 0.12)

        assert sparam.Nsteps == 81
        assert np.all(sparam.axis_2D_1 == pytest.approx(np.array([9.62, 9.74, 9.86, 9.98, 10.1, 10.22, 10.34, 10.46, 10.58])))
        assert np.all(sparam.axis_2D_2 == pytest.approx(np.array([-6.35, -6.23, -6.11, -5.99, -5.87, -5.75, -5.63, -5.51, -5.39])))
        assert np.all(sparam.axis_2D_1_indexes ==
                      np.array([4, 5, 5, 4, 3, 3, 3, 4, 5, 6, 6, 6, 6, 5, 4, 3, 2, 2, 2, 2, 2, 3,
                                4, 5, 6, 7, 7, 7, 7, 7, 7, 6, 5, 4, 3, 2, 1, 1, 1, 1, 1, 1, 1, 2,
                                3, 4, 5, 6, 7, 8, 8, 8, 8, 8, 8, 8, 8, 7, 6, 5, 4, 3, 2, 1, 0, 0,
                                0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8]))
        assert np.all(sparam.axis_2D_2_indexes ==
                      np.array([4, 4, 5, 5, 5, 4, 3, 3, 3, 3, 4, 5, 6, 6, 6, 6, 6, 5, 4, 3, 2, 2,
                                2, 2, 2, 2, 3, 4, 5, 6, 7, 7, 7, 7, 7, 7, 7, 6, 5, 4, 3, 2, 1, 1,
                                1, 1, 1, 1, 1, 1, 2, 3, 4, 5, 6, 7, 8, 8, 8, 8, 8, 8, 8, 8, 8, 7,
                                6, 5, 4, 3, 2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]))

        sparam = pymodaq.daq_utils.scanner.set_scan_spiral(10.1, -5.87, 0., 0.12)
        assert sparam.Nsteps == 1
        sparam = pymodaq.daq_utils.scanner.set_scan_spiral(10.1, -5.87, 1., 0.)
        assert sparam.Nsteps == 1

        sparam = pymodaq.daq_utils.scanner.set_scan_spiral(10.1, -5.87, 1., 0.01)
        assert sparam.Nsteps == 16384

        sparam = pymodaq.daq_utils.scanner.set_scan_spiral(10.1, -5.87, 1., 0.01, 500)
        assert sparam.Nsteps == 512

    def test_set_scan_linear(self):
        sparam = pymodaq.daq_utils.scanner.set_scan_linear(0, 0, 1, -2, 0.1, -0.3)

        assert sparam.Nsteps == 77
        assert np.all(sparam.axis_2D_1 == pytest.approx(np.array([0., 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.])))
        assert np.all(sparam.axis_2D_2 == pytest.approx(np.array([0., -0.3, -0.6, -0.9, -1.2, -1.5, -1.8])))
        assert np.all(sparam.axis_2D_1_indexes ==
                      np.array([0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,  1,  1,  1,  2,  2,  2,
                                2,  2,  2,  2,  3,  3,  3,  3,  3,  3,  3,  4,  4,  4,  4,  4,  4,
                                4,  5,  5,  5,  5,  5,  5,  5,  6,  6,  6,  6,  6,  6,  6,  7,  7,
                                7,  7,  7,  7,  7,  8,  8,  8,  8,  8,  8,  8,  9,  9,  9,  9,  9,
                                9,  9, 10, 10, 10, 10, 10, 10, 10]))
        assert np.all(sparam.axis_2D_2_indexes ==
                      np.array([0, 1, 2, 3, 4, 5, 6, 0, 1, 2, 3, 4, 5, 6, 0, 1, 2, 3, 4, 5, 6, 0,
                                1, 2, 3, 4, 5, 6, 0, 1, 2, 3, 4, 5, 6, 0, 1, 2, 3, 4, 5, 6, 0, 1,
                                2, 3, 4, 5, 6, 0, 1, 2, 3, 4, 5, 6, 0, 1, 2, 3, 4, 5, 6, 0, 1, 2,
                                3, 4, 5, 6, 0, 1, 2, 3, 4, 5, 6]))

        sparam = pymodaq.daq_utils.scanner.set_scan_linear(0, 0, 1, 2, 0.01, 0.03)
        assert sparam.Nsteps == 6767
        sparam = pymodaq.daq_utils.scanner.set_scan_linear(0, 0, 1, 2, 0.01, 0.03, False, 1000)
        assert sparam.Nsteps == 1014
        #  test back and forth
        sparambf = pymodaq.daq_utils.scanner.set_scan_linear(0, 0, 1, 2, 0.01, 0.03, True, 1000)
        assert np.all(sparam.axis_2D_1_indexes == sparambf.axis_2D_1_indexes)
        assert np.all(sparam.axis_2D_2_indexes[:len(sparam.axis_2D_2)-1] ==
                      sparambf.axis_2D_2_indexes[2*len(sparam.axis_2D_2)-1:len(sparam.axis_2D_2):-1])

        sparam = pymodaq.daq_utils.scanner.set_scan_linear(0, 0, 1, 2, 0.0, 0.03)
        assert sparam.Nsteps == 1
        sparam = pymodaq.daq_utils.scanner.set_scan_linear(0, 0, 1, 2, 0.01, 0.0)
        assert sparam.Nsteps == 1
        sparam = pymodaq.daq_utils.scanner.set_scan_linear(0, 0, 1, -2, 0.01, 0.03)
        assert sparam.Nsteps == 1
        sparam = pymodaq.daq_utils.scanner.set_scan_linear(0, 0, 0, -2, 0.01, 0.03)
        assert sparam.Nsteps == 1

    def test_set_scan_random(self):
        sparam = pymodaq.daq_utils.scanner.set_scan_random(0, 0, 1, -2, 0.1, -0.3)
        assert sparam.Nsteps == 77
        for ind, pos in enumerate(sparam.positions):
            assert sparam.axis_2D_1_indexes[ind] == np.where(sparam.axis_2D_1 == pos[0])[0][0]
            assert sparam.axis_2D_2_indexes[ind] == np.where(sparam.axis_2D_2 == pos[1])[0][0]