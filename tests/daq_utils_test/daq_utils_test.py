import numpy as np
import pytest

from pymodaq.daq_utils import daq_utils as utils
from pyqtgraph.parametertree import Parameter
from pathlib import Path
import datetime


class TestJsonConverter:
    def test_object2json(self):
        conv = utils.JsonConverter()
        assert conv.istrusted('datetime')
        d = datetime.datetime(year=2020, month=5, day=24, hour=10, minute=52, second=55)
        date = d.date()
        time = d.time()
        dstring = '{"module": "datetime", "type": "datetime", "data": "datetime.datetime(2020, 5, 24, 10, 52, 55)"}'
        datestring = '{"module": "datetime", "type": "date", "data": "datetime.date(2020, 5, 24)"}'
        timestring = '{"module": "datetime", "type": "time", "data": "datetime.time(10, 52, 55)"}'
        assert conv.object2json(d) == dstring
        assert conv.json2object(dstring) == d
        assert conv.object2json(date) == datestring
        assert conv.json2object(datestring) == date
        assert conv.object2json(time) == timestring
        assert conv.json2object(timestring) == time
        assert conv.json2object(conv.object2json([10, 5, 'yui'])) == [10, 5, 'yui']
        assert conv.json2object(conv.object2json((10, 5, 'yui'))) == (10, 5, 'yui')


class TestUnits:
    def test_Enm2cmrel(self):
        assert utils.Enm2cmrel(520, 515) == pytest.approx(186.70649738)

    def test_Ecmrel2Enm(self):
        assert utils.Ecmrel2Enm(500, 515) == pytest.approx(528.6117526)

    def test_eV2nm(self):
        assert utils.eV2nm(1.55) == pytest.approx(799.89811299)

    def test_nm2eV(self):
        assert utils.nm2eV(800) == pytest.approx(1.54980259)

    def test_eV2cm(self):
        assert utils.eV2cm(0.07) == pytest.approx(564.5880342655)

    def test_l2w(self):
        assert utils.l2w(800) == pytest.approx(2.35619449)


class TestString:
    def test_capitalize(self):
        string = 'abcdef'
        assert utils.capitalize(string) == 'Abcdef'

        assert utils.capitalize(string, 3) == 'ABCdef'

    def test_uncapitalize(self):
        string = 'ABCDef'
        assert utils.uncapitalize(string) == 'aBCDef'
        assert utils.uncapitalize(string, 3) == 'abcDef'


def test_get_data_dimension():
    shapes = [(), (1,), (10,), (5, 5)]
    scan_types = ['scan1D', 'scan2D']
    remove = [False, True]
    for shape in shapes:
        for scan in scan_types:
            for rem in remove:
                arr = np.ones((shape))
                size = arr.size
                dim = len(arr.shape)
                if dim == 1 and size == 1:
                    dim = 0
                if rem:
                    if scan.lower() == 'scan1d':
                        dim -= 1
                    if scan.lower() == 'scan2d':
                        dim -= 2
                assert utils.get_data_dimension(arr, scan, rem) == (shape, '{:d}D'.format(dim), size)


class TestScroll:
    def test_scroll_log(self):
        min_val = 50
        max_val = 51
        for scroll_val in range(101):
            assert utils.scroll_linear(scroll_val, min_val, max_val) == \
                   pytest.approx(10 ** (scroll_val * (np.log10(max_val) - np.log10(min_val)) / 100 + np.log10(min_val)),
                                 rel=1e-4)

    def test_scroll_linear(self):
        min_val = 50
        max_val = 51
        for scroll_val in range(101):
            assert utils.scroll_linear(scroll_val, min_val, max_val) == \
                   pytest.approx(scroll_val * (max_val - min_val) / 100 + min_val)


def test_ThreadCommand():
    command = 'abc'
    attributes = [1, 3]
    threadcomm = utils.ThreadCommand(command, attributes)
    assert threadcomm.command is command
    assert threadcomm.attributes is attributes


def test_Axis():
    ax = utils.Axis()
    assert 'data' in ax
    assert 'label' in ax
    assert 'units' in ax

    ax = utils.Axis(np.array([1, 2, 3, 5, 7]), 'a label', 'seconds')
    assert np.all(ax['data'] == np.array([1, 2, 3, 5, 7]))
    assert ax['label'] == 'a label'
    assert ax['units'] == 'seconds'


def test_elt_as_first_element():
    elts = ['test', 'tyuio', 'Mock', 'test2']
    elts_sorted = utils.elt_as_first_element(elts[:])
    assert elts_sorted[0] == 'Mock'
    for ind in range(1, len(elts)):
        assert elts_sorted[ind] in elts
    elts_sorted = utils.elt_as_first_element(elts[:], elts[1])
    assert elts_sorted[0] == elts[1]


def test_check_vals_in_iterable():
    with pytest.raises(Exception):
        utils.check_vals_in_iterable([1, ], [])

    assert not utils.check_vals_in_iterable([1, 2.0, 4], (1, 2, 4))
    assert not utils.check_vals_in_iterable([1, 2.0, 4], (1, 2.0, 4))
    assert not utils.check_vals_in_iterable(np.array([1, 2.0, 4]), np.array((1, 2, 4)))


def test_get_set_local_dir():
    local_path = utils.get_set_local_dir()
    assert Path(local_path).is_dir()


def test_get_set_log_path():
    local_path = utils.get_set_local_dir()
    log_path = utils.get_set_log_path()
    assert Path(log_path) == Path(local_path).joinpath('logging')
    assert Path(log_path).is_dir()


def test_get_set_pid_path():
    local_path = utils.get_set_local_dir()
    pid_path = utils.get_set_pid_path()
    assert Path(pid_path) == Path(local_path).joinpath('config_pid')
    assert Path(pid_path).is_dir()


def test_zeros_aligned():
    # just one exemple...
    align = 64
    data = utils.zeros_aligned(1230, align, np.uint32)
    assert data.ctypes.data % align == 0


def test_set_param_from_param():
    params = [
        {'title': 'Main Settings:', 'name': 'main_settings', 'expanded': False, 'type': 'group', 'children': [
            {'title': 'DAQ type:', 'name': 'DAQ_type', 'type': 'list', 'values': ['DAQ0D', 'DAQ1D', 'DAQ2D', 'DAQND'],
             'readonly': True},
            {'title': 'Detector type:', 'name': 'detector_type', 'type': 'str', 'value': '', 'readonly': True},
            {'title': 'Nviewers:', 'name': 'Nviewers', 'type': 'int', 'value': 1, 'min': 1, 'default': 1,
             'readonly': True},
        ]}
    ]
    settings = Parameter.create(name='settings', type='group', children=params)
    settings_old = Parameter.create(name='settings', type='group', children=params)

    settings.child('main_settings', 'detector_type').setValue('new string')
    utils.set_param_from_param(param_old=settings_old, param_new=settings)
    assert settings_old.child('main_settings', 'detector_type').value() == 'new string'

    settings.child('main_settings', 'DAQ_type').opts['limits'].append('new type')
    settings.child('main_settings', 'DAQ_type').setValue('new type')
    utils.set_param_from_param(param_old=settings_old, param_new=settings)
    assert settings_old.child('main_settings', 'DAQ_type').value() == 'new type'

    settings.child('main_settings', 'detector_type').setValue('')
    utils.set_param_from_param(param_old=settings_old, param_new=settings)
    assert settings_old.child('main_settings', 'detector_type').value() == 'new string'


def test_get_new_file_name(tmp_path):
    base_name = 'tttr_data'
    file, direct = utils.get_new_file_name(tmp_path, base_name)
    today = datetime.datetime.now()
    date = today.strftime('%Y%m%d')
    year = today.strftime('%Y')

    assert direct == tmp_path.joinpath(year, date)
    assert file == f'{base_name}_000'
    file, direct = utils.get_new_file_name(tmp_path, base_name)
    assert file == f'{base_name}_000'
    with open(direct.joinpath(f'{file}.h5'), 'w') as f:
        pass
    file, direct = utils.get_new_file_name(tmp_path, base_name)
    assert file == f'{base_name}_001'
    base_name = 'anotherbasename'
    file, direct = utils.get_new_file_name(tmp_path, base_name)
    assert file == f'{base_name}_000'


class TestMath():
    def test_my_moment(self):
        x = utils.linspace_step(0, 100, 1)
        y = utils.gauss1D(x, 42.321,
                          13.5)  # relation between dx in the gauss1D and in the moment is np.sqrt(4*np.log(2))

        x0, dx = utils.my_moment(x, y)
        assert x0 == pytest.approx(42.321)
        assert dx * np.sqrt(4 * np.log(2)) == pytest.approx(13.5)

    def test_odd_even(self):
        assert not utils.odd_even(10)
        assert utils.odd_even(-11)

        with pytest.raises(TypeError):
            assert utils.odd_even(11.2)

    def test_greater2n(self):
        assert utils.greater2n(127) == 128
        assert utils.greater2n(62.95) == 64

        with pytest.raises(TypeError):
            assert utils.greater2n(True)
        with pytest.raises(TypeError):
            assert utils.greater2n([10.4, 248, True])

        assert utils.greater2n([10.4, 248, 1020]) == [16, 256, 1024]
        assert np.all(utils.greater2n(np.array([10.4, 248, 1020])) == np.array([16, 256, 1024]))

    def test_linspace_step(self):
        assert np.all(utils.linspace_step(-1.0, 10, 1) == np.array([-1., 0., 1., 2., 3., 4., 5., 6., 7., 8., 9., 10.]))
        assert np.all(
            utils.linspace_step(1.0, -1, -0.13) == pytest.approx(
                np.array([1., 0.87, 0.74, 0.61, 0.48, 0.35, 0.22, 0.09, -0.04,
                          -0.17, -0.3, -0.43, -0.56, -0.69, -0.82, -0.95])))
        with pytest.raises(ValueError):
            utils.linspace_step(45, 45, 1)
        with pytest.raises(ValueError):
            utils.linspace_step(0, 10, -1)
        with pytest.raises(ValueError):
            utils.linspace_step(0, 10, 0.)

    def test_find_index(self):  # get closest value and index
        x = utils.linspace_step(1.0, -1, -0.13)
        assert utils.find_index(x, -0.55) == [(12, -0.56)]
        assert utils.find_index(x, [-0.55, 0.741]) == [(12, -0.56), (2, 0.74)]
        assert utils.find_index(x, 10) == [(0, 1.)]

    def test_gauss1D(self):
        x = utils.linspace_step(1.0, -1, -0.13)
        x0 = -0.55
        dx = 0.1
        n = 1
        assert np.all(utils.gauss1D(x, x0, dx, n) == pytest.approx(
            np.exp(-2 * np.log(2) ** (1 / n) * (((x - x0) / dx)) ** (2 * n))))
        with pytest.raises(ValueError):
            utils.gauss1D(x, x0, -0., 1)
        with pytest.raises(TypeError):
            utils.gauss1D(x, x0, 0.1, 1.1)
        with pytest.raises(ValueError):
            utils.gauss1D(x, x0, 0.1, -1)

    def test_gauss2D(self):
        x = utils.linspace_step(-1.0, 1, 0.1)
        x0 = -0.55
        dx = 0.1
        y = utils.linspace_step(-2.0, -1, 0.1)
        y0 = -1.55
        dy = 0.2
        n = 1
        assert np.all(utils.gauss2D(x, x0, dx, y, y0, dy, n) == pytest.approx(
            np.transpose(np.outer(utils.gauss1D(x, x0, dx, n), utils.gauss1D(y, y0, dy, n)))))
        assert np.all(
            utils.gauss2D(x, x0, dx, y, y0, dy, n) == pytest.approx(utils.gauss2D(x, x0, dx, y, y0, dy, n, 180)))
        assert np.all(
            utils.gauss2D(x, x0, dx, y, y0, dy, n, -90) == pytest.approx(utils.gauss2D(x, x0, dx, y, y0, dy, n, 90)))
        assert np.all(
            utils.gauss2D(x, x0, dx, y, y0, dy, n) == pytest.approx(utils.gauss2D(x, x0, dy, y, y0, dx, n, 90)))

    def test_ftAxis(self):
        omega_max = utils.l2w(800)
        Npts = 1024
        omega_grid, time_grid = utils.ftAxis(Npts, omega_max)
        assert len(omega_grid) == Npts
        assert len(time_grid) == Npts
        assert np.max(time_grid) == (Npts - 1) * np.pi / (2 * omega_max)

    def test_ftAxis_time(self):
        time_max = 10000  # fs
        Npts = 1024
        omega_grid, time_grid = utils.ftAxis_time(Npts, time_max)
        assert len(omega_grid) == Npts
        assert len(time_grid) == Npts
        assert np.max(omega_grid) == (Npts - 1) / 2 * 2 * np.pi / time_max

    def test_ft(self):
        omega_max = utils.l2w(300)
        omega0 = utils.l2w(800)
        Npts = 2 ** 10
        omega_grid, time_grid = utils.ftAxis(Npts, omega_max)
        signal_temp = np.sin(omega0 * time_grid) * utils.gauss1D(time_grid, 0, 100, 1)
        signal_omega = utils.ft(signal_temp)

        assert np.abs(omega_grid[np.argmax(np.abs(signal_omega))]) == pytest.approx(omega0, rel=1e-2)
        with pytest.raises(Exception):
            utils.ft(signal_temp, 2)

    def test_ift(self):
        omega_max = utils.l2w(300)
        omega0 = utils.l2w(800)
        Npts = 2 ** 10
        omega_grid, time_grid = utils.ftAxis(Npts, omega_max)
        signal_temp = np.sin(omega0 * time_grid) * utils.gauss1D(time_grid, 0, 100, 1)
        signal_omega = utils.ft(signal_temp)
        assert np.all(signal_temp == pytest.approx(np.real(utils.ift(signal_omega))))
        with pytest.raises(Exception):
            utils.ift(signal_temp, 2)
