import numpy as np
import pytest

import pymodaq.daq_utils
from pymodaq.daq_utils import scanner
from pymodaq.daq_utils import exceptions as exceptions


class TestScanInfo:
    def test_ScanInfo(self):
        Nsteps = 10
        axes_indexes = np.array([])
        axes_unique = np.array([])
        positions = np.array([])
        kwargs = ['test1', 'test2']
        scan_param = scanner.ScanInfo(Nsteps, positions, axes_indexes, axes_unique, kwargs=kwargs)
        assert scan_param.Nsteps is Nsteps
        assert scan_param.axes_indexes is axes_indexes
        assert scan_param.axes_unique is axes_unique
        assert scan_param.positions is positions
        assert scan_param.kwargs is kwargs

    def test__repr__(self):
        Nsteps = 10
        axes_indexes = np.array([])
        axes_unique = np.array([])
        positions = np.array([])
        scan_param = scanner.ScanInfo(Nsteps, positions, axes_indexes, axes_unique)
        assert scan_param.__repr__()

        scan_param = scanner.ScanInfo()
        assert scan_param.__repr__()

class TestScanParameters:
    def test_ScanParameters(self):
        starts = [1, 2]
        stops = [10, 20]
        steps = [1, 2]
        scan_param = scanner.ScanParameters(starts=starts, stops=stops, steps=steps)
        assert scan_param.Naxes == 1
        assert scan_param.scan_type == 'Scan1D'
        assert scan_param.scan_subtype == 'Linear'
        assert scan_param.starts == starts
        assert scan_param.stops == stops
        assert scan_param.steps == steps

        with pytest.raises(ValueError):
            scanner.ScanParameters(scan_type='test', starts=starts, stops=stops, steps=steps)

        with pytest.raises(ValueError):
            scanner.ScanParameters(scan_subtype='test', starts=starts, stops=stops, steps=steps)

    def test_getattr(self):
        starts = [1, 2]
        stops = [10, 20]
        steps = [1, 2]
        positions = np.array([[1], [2], [3], [4], [5], [6], [7], [8], [9], [10]])
        axes_indexes = np.array([[0], [1], [2], [3], [4], [5], [6], [7], [8], [9]])
        axes_unique = [np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])]
        scan_param = scanner.ScanParameters(starts=starts, stops=stops, steps=steps)
        assert scan_param.__getattr__('Nsteps') == 10
        assert np.array_equal(scan_param.__getattr__('positions'), positions)
        assert np.array_equal(scan_param.__getattr__('axes_indexes'), axes_indexes)
        assert np.array_equal(scan_param.__getattr__('axes_unique'), axes_unique)
        assert scan_param.__getattr__('adaptive_loss') == None

        with pytest.raises(ValueError):
            scan_param.__getattr__('test')

    def test_get_info_from_positions(self):
        positions = np.array([1, 2, 3, 4])
        scan_param = scanner.ScanParameters(positions=positions)
        result = scan_param.get_info_from_positions(positions)
        assert np.array_equal(result.positions, np.expand_dims(positions, 1))
        assert np.array_equal(result.axes_unique, [positions])
        assert scan_param.get_info_from_positions(None)

    def test_set_scan(self):
        # Scan1D
        positions = np.array([[1], [2], [3], [4]])
        scan_param = scanner.ScanParameters(positions=positions)
        result = scan_param.set_scan()
        assert np.array_equal(result.positions, scan_param.get_info_from_positions(positions).positions)

        scan_param = scanner.ScanParameters(positions=positions, scan_subtype='Random')
        result = scan_param.set_scan()
        for value in positions:
            assert value in result.positions

        # Scan2D
        np.array([[1, 2], [2, 3], [3, 4], [4, 5]])

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
        assert np.all(positionsbf[:ny - 1, 1] == positionsbf[2 * ny - 1:ny:-1, 1])

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
