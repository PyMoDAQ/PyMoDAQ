import os
import numpy as np
from datetime import datetime
from pathlib import Path
import pytest
import pathlib
from pytest import approx, fixture, yield_fixture
from pytest_datadir.plugin import shared_datadir, datadir
from pytestqt import qtbot
from pymodaq.version import get_version

from pymodaq.daq_utils.h5saver import H5Saver, H5Backend, is_h5py, is_h5pyd, is_tables, save_types, group_types, \
    group_data_types, data_types, data_dimensions, scan_types, InvalidGroupType, InvalidDataDimension, InvalidDataType, \
    InvalidGroupDataType, InvalidSave, InvalidScanType

tested_backend = ['tables', 'h5py', 'h5pyd']
tested_backend = ['tables', 'h5py']

@pytest.fixture(scope="module")
def session_path(tmp_path_factory):
    return tmp_path_factory.mktemp('h5data')

def check_vals_in_iterable(iterable1, iterable2):
    assert len(iterable1) == len(iterable2)
    for val1, val2 in zip(iterable1, iterable2):
        assert val1 == val2

def generate_random_data(shape, dtype=np.float):
    return (100 * np.random.rand(*shape)).astype(dtype=dtype)

@pytest.fixture(params=tested_backend)
def get_backend(request, tmp_path):
    bck = H5Backend(request.param)
    title = 'this is a test file'
    bck.open_file(tmp_path.joinpath('h5file.h5'), 'w', title)
    return bck

@pytest.fixture(params=save_types)
def get_save_type(request):
    return request.param

@pytest.fixture(params=tested_backend)
def get_h5saver(get_save_type, request, qtbot):
    return H5Saver(save_type=get_save_type, backend=request.param)

@pytest.fixture(params=tested_backend)
def get_h5saver_scan(request, qtbot):
    return H5Saver(save_type='scan', backend=request.param)



class TestH5Backend:

    @pytest.mark.parametrize('backend', tested_backend)
    def test_file_open_close(self, tmp_path, backend):
        bck = H5Backend(backend)
        title = 'this is a test file'
        h5_file = bck.open_file(tmp_path.joinpath('h5file.h5'), 'w', title)
        assert tmp_path.joinpath('h5file.h5').exists()
        assert tmp_path.joinpath('h5file.h5').is_file()
        assert bck.isopen() is True
        assert bck.get_attr(bck.root(), 'TITLE') == title
        assert bck.get_attr(bck.root(), 'pymodaq_version') == get_version()
        bck.close_file()
        assert bck.isopen() is False



    def test_attrs(self, get_backend):
        bck = get_backend
        attrs = dict(attr1='one attr', attr2=(10, 15), attr3=12.4)
        for attr in attrs:
            bck.set_attr(bck.root(), attr, attrs[attr])
        for attr in attrs:
            attr_back = bck.get_attr(bck.root(), attr)
            if hasattr(attr_back, '__iter__'):
                check_vals_in_iterable(attr_back, attrs[attr])
            else:
                assert attr_back == attrs[attr]

        attrs_back = bck.get_attr(bck.root())
        for attr in attrs:
            assert attr in attrs_back
            if hasattr(attrs[attr], '__iter__'):
                check_vals_in_iterable(attrs[attr], attrs_back[attr])
            else:
                assert attrs[attr] == attrs_back[attr]

        bck.close_file()

    @pytest.mark.parametrize('group_type', group_types)
    def test_add_group(self, get_backend, group_type):
        bck = get_backend
        title = 'this is a group'
        g3 = bck.add_group('g3', group_type, bck.root(), title=title, metadata=dict(attr1='attr1', attr2=21.4))
        assert bck.get_attr(g3, 'TITLE') == title
        assert bck.get_attr(g3, 'CLASS') == 'GROUP'
        assert bck.get_attr(g3, 'type') == group_type
        assert bck.get_attr(g3, 'attr1') == 'attr1'
        assert bck.get_attr(g3, 'attr2') == 21.4
        gtype = 'this is not a valid group type'
        with pytest.raises(InvalidGroupType):
            g4 = bck.add_group('g4', gtype, bck.root())
        bck.close_file()


    def test_group_creation(self, get_backend):
        bck = get_backend
        title = 'this is a group'
        assert bck.get_node(bck.root()) == bck.root()
        assert bck.get_node('/') == bck.root()

        g1 = bck.get_set_group(bck.root(), 'g1', title)
        g2 = bck.get_set_group('/', 'g2')
        assert bck.get_attr(g1, 'TITLE') == title
        assert bck.get_attr(g1, 'CLASS') == 'GROUP'

        assert bck.get_node_name(g2) == 'g2'

        g21 = bck.get_set_group(g2, 'g21')
        assert bck.get_node_path(g21) == '/g2/g21'
        assert bck.is_node_in_group(g2, 'g21')

        g22 = bck.get_set_group('/g2', 'g22', title='group g22')
        assert bck.get_group_by_title('/g2', 'group g22') == g22

        assert list(bck.get_children(g2)) == ['g21', 'g22']

        bck.close_file()

    def test_carray(self, get_backend):
        bck = get_backend
        g1 = bck.get_set_group(bck.root(), 'g1')
        carray1_data = np.random.rand(5, 10)
        title = 'this is a carray'
        with pytest.raises(ValueError):
            bck.create_carray(g1, 'carray0', title='')
        carray1 = bck.create_carray(g1, 'carray1', obj=carray1_data, title=title)
        assert bck.get_attr(carray1, 'dtype') == carray1_data.dtype.name
        assert bck.get_attr(carray1, 'TITLE') == title
        assert bck.get_attr(carray1, 'CLASS') == 'CARRAY'
        check_vals_in_iterable(bck.get_attr(carray1, 'shape'), carray1_data.shape)

        assert np.all(bck.read(carray1) == carray1_data)
        assert np.all(carray1[1, 2] == carray1_data[1, 2])
        with pytest.raises(ValueError):
            bck.append(carray1, carray1_data)
        bck.close_file()

    @pytest.mark.parametrize('compression', ['gzip', 'zlib'])
    @pytest.mark.parametrize('comp_level', list(range(0, 10, 3)))
    def test_carray_comp(self, get_backend, compression, comp_level):
        bck = get_backend
        g1 = bck.get_set_group(bck.root(), 'g1')
        array_data = np.random.rand(5, 10)
        # gzip and zlib filters are compatible, but zlib is used by pytables while gzip is used by h5py
        bck.define_compression(compression, comp_level)
        array1 = bck.create_carray(g1, 'carray1', obj=array_data)
        assert np.all(bck.read(array1) == array_data)

    def test_earray(self, get_backend):
        bck = get_backend
        g1 = bck.get_set_group(bck.root(), 'g1')
        title = 'this is a earray'
        dtype = np.uint32
        array = bck.create_earray(g1, 'array', dtype=dtype, title=title)
        assert bck.get_attr(array, 'TITLE') == title
        assert bck.get_attr(array, 'CLASS') == 'EARRAY'
        assert bck.get_attr(array, 'dtype') == np.dtype(dtype).name
        check_vals_in_iterable(bck.get_attr(array, 'shape'), [0])
        bck.append(array, np.array([10]))
        check_vals_in_iterable(bck.get_attr(array, 'shape'), [1])

        array_shape = (10, 3)
        array1 = bck.create_earray(g1, 'array1', dtype=dtype, data_shape=array_shape, title=title)
        bck.append(array1, generate_random_data(array_shape, dtype))
        expected_shape = [1]
        expected_shape.extend(array_shape)
        check_vals_in_iterable(bck.get_attr(array1, 'shape'), expected_shape)
        bck.append(array1, generate_random_data(array_shape, dtype))
        expected_shape[0] += 1
        check_vals_in_iterable(bck.get_attr(array1, 'shape'), expected_shape)
        bck.close_file()

    @pytest.mark.parametrize('compression', ['gzip', 'zlib'])
    @pytest.mark.parametrize('comp_level', list(range(0, 10, 3)))
    def test_earray_comp(self, get_backend, compression, comp_level):
        bck = get_backend
        g1 = bck.get_set_group(bck.root(), 'g1')
        array_shape = (10, 3)
        dtype = np.uint32
        bck.define_compression(compression, comp_level)
        array = bck.create_earray(g1, 'array', dtype=dtype, data_shape=array_shape)
        data = generate_random_data(array_shape, dtype)
        bck.append(array, data)
        assert np.all(array[-1, :, :] == data)
        bck.append(array, data)
        assert np.all(array[-1, :, :] == data)


    def test_vlarray(self, get_backend):
        bck = get_backend
        g1 = bck.get_set_group(bck.root(), 'g1')
        title = 'this is a vlarray'
        dtype = np.uint32
        array = bck.create_vlarray(g1, 'array', dtype=dtype, title=title)
        assert bck.get_attr(array, 'TITLE') == title
        assert bck.get_attr(array, 'CLASS') == 'VLARRAY'
        assert bck.get_attr(array, 'dtype') == np.dtype(dtype).name

        bck.append(array, np.array([10, 12, 15]))
        assert isinstance(array[-1], np.ndarray)
        assert np.all(array[-1] == np.array([10, 12, 15]))

        bck.append(array, np.array([10, 4, 2, 4, 6, 4]))
        assert np.all(array[-1] == [10, 4, 2, 4, 6, 4])

    def test_vlarray_string(self, get_backend):
        bck = get_backend
        g1 = bck.get_set_group(bck.root(), 'g1')
        title = 'this is a vlarray'
        dtype = 'string'
        array = bck.create_vlarray(g1, 'array', dtype=dtype, title=title)
        assert bck.get_attr(array, 'TITLE') == title
        assert bck.get_attr(array, 'CLASS') == 'VLARRAY'
        assert bck.get_attr(array, 'dtype') == np.dtype(np.uint8).name
        assert bck.get_attr(array, 'subdtype') == 'string'
        st = 'this is a string'
        st2 = 'this is a second string'
        assert bck.array_to_string(bck.string_to_array(st)) == st

        bck.append(array, bck.string_to_array(st))
        assert bck.array_to_string(array[-1]) == st

        bck.append_string(array, st2)
        assert bck.array_to_string(array[-1]) == st2

class TestH5Saver():

    def test_init_file_addhoc(self, get_h5saver, tmp_path):
        h5saver = get_h5saver
        addhoc_file_path = tmp_path.joinpath('h5file.h5')
        h5saver.init_file(update_h5=True, addhoc_file_path=addhoc_file_path,
                          metadata=dict(attr1='attr1', attr2=(10, 2)))
        assert h5saver.h5_file_path == addhoc_file_path.parent
        assert h5saver.h5_file_name == addhoc_file_path.name
        assert h5saver.settings.child(('current_h5_file')).value() == str(addhoc_file_path)
        assert h5saver.current_scan_group is None
        assert h5saver.get_node_path(h5saver.raw_group) == '/Raw_datas'
        assert h5saver.get_node_path(h5saver.logger_array) == '/Raw_datas/Logger'
        assert h5saver.get_attr(h5saver.logger_array, 'data_dimension') == '0D'
        assert h5saver.get_attr(h5saver.logger_array, 'scan_type') == 'scan1D'
        assert h5saver.get_attr(h5saver.logger_array, 'dtype') == np.dtype(np.uint8).name
        assert h5saver.get_attr(h5saver.logger_array, 'subdtype') == 'string'
        assert h5saver.get_last_scan() is None
        assert h5saver.get_attr(h5saver.raw_group, 'type') == h5saver.settings.child(('save_type')).value()
        assert h5saver.get_attr(h5saver.root(), 'date') == datetime.now().date().isoformat()
        assert h5saver.get_attr(h5saver.raw_group, 'attr1') == 'attr1'
        check_vals_in_iterable(h5saver.get_attr(h5saver.raw_group, 'attr2'), (10, 2))

    def test_init_file(self, get_h5saver, tmp_path):
        h5saver = get_h5saver_scan
        datetime_now = datetime.now()
        date = datetime_now.date()
        today = f'{date.year}{date.month}{date.day}'
        base_path = tmp_path
        h5saver.settings.child(('base_path')).setValue(base_path)
        update_h5 = True
        scan_path, current_scan_name, save_path = h5saver.update_file_paths(update_h5)
        assert scan_path == tmp_path.joinpath(date.year).joinpath(today).joinpath(f'Dataset_{today}_000')
        assert current_scan_name == 'Scan000'
        assert save_path == tmp_path.joinpath(date.year).joinpath(today).joinpath(f'Dataset_{today}_000')

        h5saver.init_file(update_h5=update_h5)
        h5saver.add_scan_group()
        h5saver.add_scan_group()
        assert check_vals_in_iterable(h5saver.get_children(h5saver.raw_group), ['Scan000', 'Scan001'])
