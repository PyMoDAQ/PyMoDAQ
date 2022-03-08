import numpy as np
import os

import pymodaq.daq_utils.config
import pytest
import re

from pymodaq.daq_utils import daq_utils as utils
from pyqtgraph.parametertree import Parameter
from pathlib import Path
import datetime


class MockEntryPoints:
    def __init__(self, value):
        self.value = value


def test_get_version():
    version = utils.get_version()
    assert bool(re.match("[0-9].[0-9].[0-9]", version))


def test_get_set_local_dir():
    local_path = pymodaq.daq_utils.config.get_set_local_dir()
    assert Path(local_path).is_dir()


def test_check_config():
    dict1 = {'name': 'test', 'status': True}
    dict2 = {'name': 'test_2', 'status': False}
    dict3 = {'status': None}
    assert not pymodaq.daq_utils.config.check_config(dict1, dict2)
    assert pymodaq.daq_utils.config.check_config(dict1, dict3)
    assert dict1 == {'name': 'test', 'status': True}
    assert dict2 == {'name': 'test_2', 'status': False}
    assert dict3 == {'status': None, 'name': 'test'}


class TestJsonConverter:
    def test_object2json(self):
        conv = utils.JsonConverter()
        assert isinstance(conv, utils.JsonConverter)
        assert conv.istrusted('bytes')
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

        assert conv.json2object(conv.object2json(1j)) == {'module': 'builtins', 'type': 'complex', 'data': '1j'}
        assert isinstance(conv.json2object(conv), utils.JsonConverter)


class TestUnits:
    def test_Enm2cmrel(self):
        assert utils.Enm2cmrel(520, 515) == pytest.approx(186.70649738)

    def test_Ecmrel2Enm(self):
        assert utils.Ecmrel2Enm(500, 515) == pytest.approx(528.6117526)

    def test_eV2nm(self):
        assert utils.eV2nm(1.55) == pytest.approx(799.89811299)

    def test_nm2eV(self):
        assert utils.nm2eV(800) == pytest.approx(1.54980259)

    def test_E_J2eV(self):
        assert utils.E_J2eV(1e-18) == pytest.approx(6.24151154)

    def test_eV2cm(self):
        assert utils.eV2cm(0.07) == pytest.approx(564.5880342655)

    def test_nm2cm(self):
        assert utils.nm2cm(0.04) == pytest.approx(0.0000025)

    def test_cm2nm(self):
        assert utils.cm2nm(1e5) == pytest.approx(100)

    def test_eV2E_J(self):
        assert utils.eV2E_J(800) == pytest.approx(1.2817408e-16)

    def test_eV2radfs(self):
        assert utils.eV2radfs(1.55) == pytest.approx(2.3548643)

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
    shapes = [(), (1,), (10,), (5, 5), (2, 2, 2)]
    scan_types = ['scan1D', 'scan2D', 'scanND']
    remove = [False, True]
    for shape in shapes:
        for scan in scan_types:
            for rem in remove:
                arr = np.ones(shape)
                size = arr.size
                dim = len(arr.shape)
                if dim == 1 and size == 1:
                    dim = 0
                if rem:
                    if scan.lower() == 'scan1d':
                        dim -= 1
                    if scan.lower() == 'scan2d':
                        dim -= 2
                else:
                    if dim > 2:
                        dim = 'N'
                assert utils.get_data_dimension(arr, scan, rem) == (shape, f'{dim}D', size)


class TestScroll:
    def test_scroll_log(self):
        min_val = 50
        max_val = 51
        for scroll_val in range(101):
            assert utils.scroll_log(scroll_val, min_val, max_val) == \
                   pytest.approx(10 ** (scroll_val * (np.log10(max_val) - np.log10(min_val)) / 100 + np.log10(min_val)),
                                 rel=1e-4)

    def test_scroll_linear(self):
        min_val = 50
        max_val = 51
        for scroll_val in range(101):
            assert utils.scroll_linear(scroll_val, min_val, max_val) == \
                   pytest.approx(scroll_val * (max_val - min_val) / 100 + min_val)


def test_getLineInfo():
    try:
        1 / 0
    except Exception:
        assert utils.getLineInfo()


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

    assert ax.label == ax['label']

    ax = utils.Axis(np.array([1, 2, 3, 5, 7]), 'a label', 'seconds')
    assert np.all(ax['data'] == np.array([1, 2, 3, 5, 7]))
    assert ax['label'] == 'a label'
    assert ax['units'] == 'seconds'

    ax = utils.Axis(label=None, units=None)
    assert ax['label'] == ''
    assert ax['units'] == ''

    with pytest.raises(TypeError):
        utils.Axis(10)
    with pytest.raises(TypeError):
        utils.Axis(label=10)
    with pytest.raises(TypeError):
        utils.Axis(units=10)


def test_NavAxis():
    navaxis_tmp = utils.NavAxis(nav_index=1)
    assert isinstance(navaxis_tmp, utils.NavAxis)
    assert navaxis_tmp['nav_index'] == 1
    with pytest.raises(ValueError):
        utils.NavAxis()


class TestData:
    def test_Data(self):
        name = 'data_test'
        x = utils.linspace_step(1, 100, 1)
        y = utils.linspace_step(0.01, 1, 0.01)
        data_test = utils.Data(name=name, x_axis=x, y_axis=y)
        assert isinstance(data_test, utils.Data)
        assert data_test['name'] == name
        assert data_test['x_axis'] == utils.Axis(data=x)
        assert data_test['y_axis'] == utils.Axis(data=y)

        x = utils.Axis(x)
        y = utils.Axis(y)
        kwargs = [1, 2.0, 'kwargs', True, None]
        data_test = utils.Data(name=name, x_axis=x, y_axis=y, kwargs=kwargs)
        assert data_test['x_axis'] == x
        assert data_test['y_axis'] == y
        assert data_test['kwargs'] == kwargs

        with pytest.raises(TypeError):
            utils.Data(name=None)
        with pytest.raises(TypeError):
            utils.Data(source=None)
        with pytest.raises(ValueError):
            utils.Data(source='source')

        with pytest.raises(TypeError):
            utils.Data(distribution=None)
        with pytest.raises(ValueError):
            utils.Data(distribution='distribution')

        with pytest.raises(TypeError):
            utils.Data(x_axis=10)
        with pytest.raises(TypeError):
            utils.Data(y_axis=10)

    def test_DataFromPlugins(self):
        data = [utils.linspace_step(1, 100, 1), utils.linspace_step(0.01, 1, 0.01)]
        nav_axes = ["test"]
        x_axis = utils.Axis(data=utils.linspace_step(1, 100, 1))
        y_axis = utils.Axis(data=utils.linspace_step(1, 100, 1))
        data_test = utils.DataFromPlugins(data=data, nav_axes=nav_axes, nav_x_axis=x_axis, nav_y_axis=y_axis)
        assert isinstance(data_test, utils.DataFromPlugins)
        assert data_test['data'] == data
        assert data_test['nav_axes'] == nav_axes
        assert data_test['nav_x_axis'] == x_axis
        assert data_test['nav_y_axis'] == y_axis
        assert data_test['dim'] == 'Data1D'
        data = [np.array([1])]
        data_test = utils.DataFromPlugins(data=data)
        assert data_test['dim'] == 'Data0D'
        data = [np.array([[1, 1], [1, 2]])]
        data_test = utils.DataFromPlugins(data=data)
        assert data_test['dim'] == 'Data2D'
        data = [np.array([[[1, 1], [1, 2]], [[2, 1], [2, 2]]])]
        data_test = utils.DataFromPlugins(data=data)
        assert data_test['dim'] == 'DataND'

        with pytest.raises(TypeError):
            utils.DataFromPlugins(data=[1, 2, 3, 4, 5])
        with pytest.raises(TypeError):
            utils.DataFromPlugins(data="str")

    def test_DataToExport(self):
        data = np.array([1])
        data_test = utils.DataToExport(data=data)
        assert isinstance(data_test, utils.DataToExport)
        assert data_test['data'] == data
        assert data_test['dim'] == 'Data0D'
        data_test = utils.DataToExport()
        assert data_test['dim'] == 'Data0D'
        data = np.array([1, 1])
        data_test = utils.DataToExport(data=data)
        assert data_test['dim'] == 'Data1D'
        data = np.array([[1, 1], [1, 2]])
        data_test = utils.DataToExport(data=data)
        assert data_test['dim'] == 'Data2D'
        data = np.array([[[1, 1], [1, 2]], [[2, 1], [2, 2]]])
        data_test = utils.DataToExport(data=data)
        assert data_test['dim'] == 'DataND'

        with pytest.raises(TypeError):
            utils.DataToExport(data="data")


def test_ScaledAxis():
    scaled_axis = utils.ScaledAxis()
    assert isinstance(scaled_axis, utils.ScaledAxis)
    assert scaled_axis['offset'] == 0
    assert scaled_axis['scaling'] == 1

    with pytest.raises(TypeError):
        utils.ScaledAxis(offset=None)
    with pytest.raises(TypeError):
        utils.ScaledAxis(scaling=None)
    with pytest.raises(ValueError):
        utils.ScaledAxis(scaling=0)

    assert scaled_axis['scaling'] == scaled_axis.scaling


def test_ScalingOptions():
    scaling_options = utils.ScalingOptions(utils.ScaledAxis(), utils.ScaledAxis())
    assert isinstance(scaling_options, utils.ScalingOptions)
    assert isinstance(scaling_options['scaled_xaxis'], utils.ScaledAxis)
    assert isinstance(scaling_options['scaled_yaxis'], utils.ScaledAxis)


def test_recursive_find_files_extension():
    path = Path(os.path.dirname(os.path.realpath(__file__)))
    assert path.is_dir()
    ext = 'py'
    assert utils.recursive_find_files_extension(path, ext)


def test_recursive_find_exp_in_files():
    path = Path(os.path.dirname(os.path.realpath(__file__)))
    assert path.is_dir()
    exp = 'import pytest'
    assert utils.recursive_find_expr_in_files(path, exp)


def test_remove_spaces():
    assert utils.remove_spaces("ab cd") == "abcd"
    assert utils.remove_spaces("a b c  d") == "abcd"
    assert utils.remove_spaces("abcd") == "abcd"


def test_rint():
    x1 = 15.49
    x2 = 15.51
    y1 = utils.rint(x1)
    y2 = utils.rint(x2)
    assert y1 == 15
    assert isinstance(y1, int)
    assert y2 == 16
    assert isinstance(y2, int)


def test_elt_as_first_element():
    elts = ['test', 'tyuio', 'Mock', 'test2']
    elts_sorted = utils.elt_as_first_element(elts[:])
    assert elts_sorted[0] == 'Mock'
    for ind in range(1, len(elts)):
        assert elts_sorted[ind] in elts
    elts_sorted = utils.elt_as_first_element(elts[:], elts[1])
    assert elts_sorted[0] == elts[1]
    assert utils.elt_as_first_element([]) == []
    with pytest.raises(TypeError):
        utils.elt_as_first_element(10)
    with pytest.raises(TypeError):
        utils.elt_as_first_element([1, 2, 3])


def test_elt_as_first_element_dicts():
    dict1 = {"module": "Empty", "name": "1D"}
    dict2 = {"module": "Empty", "name": "Mock"}
    elts_sorted = utils.elt_as_first_element_dicts([dict1, dict2])
    assert elts_sorted[0] == {"module": "Empty", "name": "Mock"}
    assert not utils.elt_as_first_element_dicts([])
    with pytest.raises(TypeError):
        utils.elt_as_first_element_dicts(10)
    with pytest.raises(TypeError):
        utils.elt_as_first_element_dicts([1, 2, 3])


# def test_get_plugins():  # run on local with pytest option --import-mode=importlib
#     assert utils.get_plugins()
#     assert utils.get_plugins('daq_move')
    

def test_check_vals_in_iterable():
    with pytest.raises(Exception):
        utils.check_vals_in_iterable([1, ], [])

    assert not utils.check_vals_in_iterable([1, 2.0, 4], (1, 2, 4))
    assert not utils.check_vals_in_iterable([1, 2.0, 4], (1, 2.0, 4))
    assert not utils.check_vals_in_iterable(np.array([1, 2.0, 4]), np.array((1, 2, 4)))


class TestGetSet:
    def test_get_set_config_path(self):
        local_path = pymodaq.daq_utils.config.get_set_local_dir()
        config_path = pymodaq.daq_utils.config.get_set_config_path()
        assert Path(config_path) == Path(local_path).joinpath('config')
        assert Path(config_path).is_dir()

    def test_get_set_preset_path(self):
        local_path = pymodaq.daq_utils.config.get_set_local_dir()
        preset_path = pymodaq.daq_utils.config.get_set_preset_path()
        assert Path(preset_path) == Path(local_path).joinpath('preset_configs')
        assert Path(preset_path).is_dir()

    def test_get_set_pid_path(self):
        local_path = pymodaq.daq_utils.config.get_set_local_dir()
        pid_path = pymodaq.daq_utils.config.get_set_pid_path()
        assert Path(pid_path) == Path(local_path).joinpath('pid_configs')
        assert Path(pid_path).is_dir()

    def test_get_set_log_path(self):
        local_path = pymodaq.daq_utils.config.get_set_local_dir()
        log_path = pymodaq.daq_utils.config.get_set_log_path()
        assert Path(log_path) == Path(local_path).joinpath('log')
        assert Path(log_path).is_dir()

    def test_get_set_layout_path(self):
        local_path = pymodaq.daq_utils.config.get_set_local_dir()
        layout_path = pymodaq.daq_utils.config.get_set_layout_path()
        assert Path(layout_path) == Path(local_path).joinpath('layout_configs')
        assert Path(layout_path).is_dir()

    def test_get_set_remote_path(self):
        local_path = pymodaq.daq_utils.config.get_set_local_dir()
        remote_path = pymodaq.daq_utils.config.get_set_remote_path()
        assert Path(remote_path) == Path(local_path).joinpath('remote_configs')
        assert Path(remote_path).is_dir()

    def test_get_set_overshoot_path(self):
        local_path = pymodaq.daq_utils.config.get_set_local_dir()
        overshoot_path = pymodaq.daq_utils.config.get_set_overshoot_path()
        assert Path(overshoot_path) == Path(local_path).joinpath('overshoot_configs')
        assert Path(overshoot_path).is_dir()

    def test_get_set_roi_path(self):
        local_path = pymodaq.daq_utils.config.get_set_local_dir()
        roi_path = pymodaq.daq_utils.config.get_set_roi_path()
        assert Path(roi_path) == Path(local_path).joinpath('roi_configs')
        assert Path(roi_path).is_dir()

    def test_get_module_name(self):
        config_path = pymodaq.daq_utils.config.get_set_config_path()
        assert utils.get_module_name(config_path) == 'config'


def test_zeros_aligned():
    # just one example...
    align = 64
    data = utils.zeros_aligned(1230, align, np.uint32)
    assert data.ctypes.data % align == 0


def test_set_param_from_param():
    params = [
        {'title': 'Main Settings:', 'name': 'main_settings', 'expanded': False, 'type': 'group', 'children': [
            {'title': 'DAQ type:', 'name': 'DAQ_type', 'type': 'list', 'limits': ['DAQ0D', 'DAQ1D', 'DAQ2D', 'DAQND'],
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

    file_path = str(tmp_path)
    file, direct = utils.get_new_file_name(file_path, base_name)
    assert file == f'{base_name}_000'


def test_find_dict_if_matched_key_val(self):
    dict_tmp = {1: 'abc', 2: 'def'}
    assert utils.find_dict_if_matched_key_val(dict_tmp, 1, 'abc')
    assert not utils.find_dict_if_matched_key_val(dict_tmp, 2, 'abc')


def test_find_dict_in_list_from_key_val(self):
    dict_tmp_1 = {1: 'abc', 2: 'def'}
    dict_tmp_2 = {1: 'def', 2: 'abc'}
    dict_tmp_3 = {'abc': 1, 'def': 2}
    dicts = [dict_tmp_1, dict_tmp_2, dict_tmp_3]

    assert utils.find_dict_in_list_from_key_val(dicts, 1, 'abc') == dict_tmp_1
    assert utils.find_dict_in_list_from_key_val(dicts, 1, 'abc', True) == tuple([dict_tmp_1, 0])

    assert utils.find_dict_in_list_from_key_val(dicts, 'def', 1) is None
    assert utils.find_dict_in_list_from_key_val(dicts, 'def', 1, True) == tuple([None, -1])