import numpy as np
import os
import pytest
import re
from pathlib import Path
import datetime

from pymodaq.utils import daq_utils as utils


class MockEntryPoints:
    def __init__(self, value):
        self.value = value


class MockObject:
    def __init__(self, **kwargs):
        for key in kwargs:
            setattr(self, key, kwargs[key])


def test_get_version():
    version = utils.get_version()
    assert bool(re.match("[0-9].[0-9].[0-9]", version))


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


class TestString:
    def test_capitalize(self):
        string = 'abcdef'
        assert utils.capitalize(string) == 'Abcdef'
        assert utils.capitalize(string, 3) == 'ABCdef'

    def test_uncapitalize(self):
        string = 'ABCDef'
        assert utils.uncapitalize(string) == 'aBCDef'
        assert utils.uncapitalize(string, 3) == 'abcDef'



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
    assert threadcomm.attribute is attributes


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


def test_get_entry_points():
    discovered_entrypoints = utils.get_entrypoints('pymodaq.instruments')
    discovered_entrypoints.extend(utils.get_entrypoints('pymodaq.plugins'))
    assert len(discovered_entrypoints) > 0

    names = [entry.name for entry in discovered_entrypoints]
    assert 'mock' in names

    discovered_entrypoints = utils.get_entrypoints('pymodaq.pid_models')
    discovered_entrypoints = utils.get_entrypoints('pymodaq.extensions')


def test_get_plugins():  # run on local with pytest option --import-mode=importlib
    assert 'Mock' in [plug['name'] for plug in utils.get_plugins()]
    assert 'Mock' in [plug['name'] for plug in utils.get_plugins('daq_move')]
    assert 'Mock' in [plug['name'] for plug in utils.get_plugins('daq_0Dviewer')]
    assert 'Mock' in [plug['name'] for plug in utils.get_plugins('daq_1Dviewer')]
    assert 'Mock' in [plug['name'] for plug in utils.get_plugins('daq_2Dviewer')]


def test_check_vals_in_iterable():
    with pytest.raises(Exception):
        utils.check_vals_in_iterable([1, ], [])

    assert not utils.check_vals_in_iterable([1, 2.0, 4], (1, 2, 4))
    assert not utils.check_vals_in_iterable([1, 2.0, 4], (1, 2.0, 4))
    assert not utils.check_vals_in_iterable(np.array([1, 2.0, 4]), np.array((1, 2, 4)))


def test_zeros_aligned():
    # just one example...
    align = 64
    data = utils.zeros_aligned(1230, align, np.uint32)
    assert data.ctypes.data % align == 0


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


class TestFindInIterable:

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

    def test_find_object_if_matched_attr_name_val(self):
        obj = MockObject(attr1=12, attr2='ghj')
        assert utils.find_object_if_matched_attr_name_val(obj, 'attr1', 12)
        assert utils.find_object_if_matched_attr_name_val(obj, 'attr2', 'ghj')
        assert not utils.find_object_if_matched_attr_name_val(obj, 'attr3', 12)
        assert not utils.find_object_if_matched_attr_name_val(obj, 'attr2', 12)

    def find_objects_in_list_from_attr_name_val(self):
        objects = [MockObject(attr1=elt1, attr2=elt2) for elt1, elt2 in zip(['abc', 'abc', 'bgf'], [12, 45, 45])]

        assert utils.find_objects_in_list_from_attr_name_val(objects, 'attr1', 'abc') == objects[0], 0
        selection = utils.find_objects_in_list_from_attr_name_val(objects, 'attr1', 'abc', return_first=False)
        assert len(selection) == 2
        assert selection[0] == objects[0], 0
        assert selection[1] == objects[1], 1

        selection = utils.find_objects_in_list_from_attr_name_val(objects, 'attr2', 45, return_first=False)
        assert len(selection) == 2
        assert selection[0] == objects[1], 1
        assert selection[1] == objects[2], 2
