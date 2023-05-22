import os
import numpy as np
from datetime import datetime
import pytest
from pathlib import PurePosixPath, Path

from pymodaq.utils import daq_utils as utils
from pymodaq.utils.h5modules import backends


tested_backend = []
try:
    import tables
    tested_backend.append('tables')
except ImportError:
    pass
try:
    import h5py
    tested_backend.append('h5py')
except ImportError:
    pass
try:
    import h5pyd
    tested_backend.append('h5pyd')
except ImportError:
    pass


@pytest.fixture(scope="module")
def session_path(tmp_path_factory):
    return tmp_path_factory.mktemp('h5data')


def generate_random_data(shape, dtype=float):
    return (100 * np.random.rand(*shape)).astype(dtype=dtype)


@pytest.fixture(params=tested_backend)
def get_backend(request, tmp_path):
    bck = backends.H5Backend(request.param)
    title = 'this is a test file'
    start_path = get_temp_path(tmp_path, request.param)
    bck.open_file(start_path.joinpath('h5file.h5'), 'w', title)
    yield bck
    bck.close_file()


def get_temp_path(tmp_path, backend='h5pyd'):
    if backend == 'h5pyd':
        return PurePosixPath('/home/pymodaq_user/test_backend/')
    else:
        return tmp_path


def test_check_mandatory_attrs():
    attr_name = 'TITLE'
    attr = b'test'
    result = backends.check_mandatory_attrs(attr_name, attr)
    assert result == 'test'
    attr = f'test'
    result = backends.check_mandatory_attrs(attr_name, attr)
    assert result == f'test'
    attr_name = 'TEST'
    result = backends.check_mandatory_attrs(attr_name, attr)
    assert result == f'test'


class TestNode:
    @pytest.mark.parametrize('backend', tested_backend)
    def test_init(self, backend):
        node_dict = {'NAME': 'Node', 'TITLE': 'test'}
        node_obj = backends.Node(node_dict, backend)
        assert isinstance(node_obj, backends.Node)
        assert node_obj.node == node_dict
        assert node_obj.backend == backend

        node_obj_2 = backends.Node(node_obj, backend)
        assert node_obj_2.node == node_dict

    def test_h5file(self, get_backend):
        bck = get_backend
        attrs = dict(attr1='one attr', attr2=(10, 15), attr3=12.4)
        node = bck.add_group('mygroup', 'detector', '/', metadata=attrs)

        assert isinstance(node, backends.Node)
        assert node.h5file is not None

    def test_to_backend(self, get_backend):
        bck = get_backend
        attrs = dict(attr1='one attr', attr2=(10, 15), attr3=12.4)
        node = bck.add_group('mygroup', 'detector', '/', metadata=attrs)

        bck_bis = node.to_h5_backend()
        assert bck_bis.h5file == node.h5file
        group_node = bck_bis.get_node('/Mygroup')
        assert group_node == node


class TestH5Backend:
    @pytest.mark.parametrize('backend', tested_backend)
    def test_file_open_close(self, tmp_path, backend):
        bck = backends.H5Backend(backend)
        title = 'this is a test file'
        start_path = get_temp_path(tmp_path, backend)
        h5_file = bck.open_file(start_path.joinpath('h5file.h5'), 'w', title)
        if backend != 'h5pyd':
            assert start_path.joinpath('h5file.h5').exists()
            assert start_path.joinpath('h5file.h5').is_file()

        assert bck.isopen() is True
        assert bck.root().attrs['TITLE'] == title
        assert bck.root().attrs['pymodaq_version'] == utils.get_version()
        bck.close_file()
        assert bck.isopen() is False

        bck = backends.H5Backend(backend)
        assert bck.isopen() is False

    def test_attrs(self, get_backend):
        bck = get_backend
        attrs = dict(attr1='one attr', attr2=(10, 15), attr3=12.4)
        for attr in attrs:
            bck.root().attrs[attr] = attrs[attr]
        for attr in attrs:
            attr_back = bck.root().attrs[attr]
            if hasattr(attr_back, '__iter__'):
                utils.check_vals_in_iterable(attr_back, attrs[attr])
            else:
                assert attr_back == attrs[attr]

        attrs_back = bck.root().attrs.attrs_name
        for attr in attrs:
            assert attr in attrs_back
            if hasattr(attrs[attr], '__iter__'):
                utils.check_vals_in_iterable(attrs[attr], bck.root().attrs[attr])
            else:
                assert attrs[attr] == bck.root().attrs[attr]

        bck.close_file()

    @pytest.mark.parametrize('group_type', backends.GroupType.names())
    def test_add_group(self, get_backend, group_type):
        bck = get_backend
        title = 'this is a group'
        g3 = bck.add_group('g3', group_type, bck.root(), title=title, metadata=dict(attr1='attr1', attr2=21.4))
        assert g3.attrs['TITLE'] == title
        assert g3.attrs['CLASS'] == 'GROUP'
        assert g3.attrs['type'] == group_type
        assert g3.attrs['attr1'] == 'attr1'
        assert g3.attrs['attr2'] == 21.4
        gtype = 'this is not a valid group type'
        with pytest.raises(ValueError):
            g4 = bck.add_group('g4', gtype, bck.root())
        bck.close_file()

    def test_group_creation(self, get_backend):
        bck = get_backend
        title = 'this is a group'
        assert bck.get_node(bck.root()) == bck.root()
        assert bck.get_node('/') == bck.root()

        g1 = bck.get_set_group(bck.root(), 'g1', title)
        g2 = bck.get_set_group('/', 'g2')
        assert g1.attrs['TITLE'] == title
        assert g1.attrs['CLASS'] == 'GROUP'

        assert bck.get_node_name(g2) == 'g2'

        g21 = bck.get_set_group(g2, 'g21')
        assert bck.get_node_path(g21) == '/g2/g21'
        assert bck.is_node_in_group(g2, 'g21')

        g22 = bck.get_set_group('/g2', 'g22', title='group g22')
        assert bck.get_group_by_title('/g2', 'group g22') == g22

        assert list(bck.get_children(g2)) == ['g21', 'g22']

        assert bck.get_parent_node(g22) == g2
        assert bck.get_parent_node(bck.get_parent_node(g2)) is None
        assert g22.parent_node == g2
        assert g2.parent_node.parent_node is None

        assert isinstance(g2, backends.Node)
        assert isinstance(g22, backends.Node)

        # test node methods
        assert g2 != g1

        assert g22.parent_node == g2
        assert g22.parent_node == g21.parent_node
        utils.check_vals_in_iterable(g2.children_name(), ['g21', 'g22'])
        for child in g2.children():
            assert g2.children()[child] in [g21, g22]
        g22.set_attr('test', 12.5)
        assert g22.get_attr('test') == 12.5
        assert g22.attrs['test'] == 12.5
        g22.attrs['test1'] = 'attr'
        assert g22.attrs['test1'] == 'attr'
        assert isinstance(g22.attrs, backends.Attributes)
        assert g21.name == 'g21'
        assert bck.root().name == '/'
        assert g22.path == '/g2/g22'

        bck.close_file()

    def test_walk_groups(self, get_backend):
        bck = get_backend
        g1 = bck.get_set_group(bck.root(), 'g1')
        g2 = bck.get_set_group('/', 'g2')
        g21 = bck.get_set_group(g2, 'g21')
        g22 = bck.get_set_group('/g2', 'g22', title='group g22')
        groups = ['/', 'g1', 'g2', 'g22', 'g21']
        gps = []
        for gr in bck.walk_groups('/'):
            assert gr.attrs['CLASS'] == 'GROUP'
            gps.append(gr.name)
        assert len(gps) == len(groups)
        for gr in gps:
            assert gr in groups

    def test_walk_nodes(self, get_backend):
        bck = get_backend
        g1 = bck.get_set_group(bck.root(), 'g1')
        array_g1 = bck.create_carray(g1, 'array_g1', np.array([1, 2, 3, 4, 5, 6]))
        g2 = bck.get_set_group('/', 'g2')
        array_g2 = bck.create_carray(g2, 'array_g2', np.array([1, 2, 3, 4, 5, 6]))
        g21 = bck.get_set_group(g2, 'g21')
        g22 = bck.get_set_group('/g2', 'g22', title='group g22')
        array_g22 = bck.create_carray(g22, 'array_g22', np.array([1, 2, 3, 4, 5, 6]))
        nodes = ['/', 'g1', 'g2', 'array_g2', 'g22', 'g21', 'array_g1', 'array_g22']
        gps = []
        for gr in bck.walk_nodes('/'):
            gps.append(gr.name)
        assert len(gps) == len(nodes)
        for gr in gps:
            assert gr in nodes

    def test_carray(self, get_backend):
        bck = get_backend
        g1 = bck.get_set_group(bck.root(), 'g1')
        carray1_data = np.random.rand(5, 10)
        title = 'this is a carray'
        with pytest.raises(ValueError):
            bck.create_carray(g1, 'carray0', title='')
        carray1 = bck.create_carray(g1, 'carray1', obj=carray1_data, title=title)
        assert isinstance(carray1, backends.CARRAY)
        assert carray1.attrs['dtype'] == carray1_data.dtype.name
        assert carray1.attrs['TITLE'] == title
        assert carray1.attrs['CLASS'] == 'CARRAY'
        utils.check_vals_in_iterable(carray1.attrs['shape'], carray1_data.shape)

        assert np.all(carray1.read() == pytest.approx(carray1_data))
        assert np.all(carray1[1, 2] == pytest.approx(carray1_data[1, 2]))
        with pytest.raises(AttributeError):
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
        assert np.all(array1.read() == pytest.approx(array_data))

    def test_earray(self, get_backend):
        bck = get_backend
        g1 = bck.get_set_group(bck.root(), 'g1')
        title = 'this is a earray'
        dtype = np.uint32
        array = bck.create_earray(g1, 'array', dtype=dtype, title=title)
        assert array.attrs['TITLE'] == title
        assert array.attrs['CLASS'] == 'EARRAY'
        assert array.attrs['dtype'] == np.dtype(dtype).name
        utils.check_vals_in_iterable(array.attrs['shape'], [0])
        array.append(np.array([10]))
        assert g1.children()['array'] == array
        assert isinstance(g1.children()['array'], backends.EARRAY)
        utils.check_vals_in_iterable(array.attrs['shape'], [1])

        array_shape = (10, 3)
        array1 = bck.create_earray(g1, 'array1', dtype=dtype, data_shape=array_shape, title=title)
        array1.append(generate_random_data(array_shape, dtype))
        expected_shape = [1]
        expected_shape.extend(array_shape)
        utils.check_vals_in_iterable(array1.attrs['shape'], expected_shape)
        array1.append(generate_random_data(array_shape, dtype))
        expected_shape[0] += 1
        utils.check_vals_in_iterable(array1.attrs['shape'], expected_shape)
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
        array.append(data)
        assert np.all(array[-1, :, :] == pytest.approx(data))
        array.append(data)
        assert np.all(array[-1, :, :] == pytest.approx(data))

    def test_vlarray(self, get_backend):
        bck = get_backend
        g1 = bck.get_set_group(bck.root(), 'g1')
        title = 'this is a vlarray'
        dtype = np.uint32
        array = bck.create_vlarray(g1, 'array', dtype=dtype, title=title)
        assert array.attrs['TITLE'] == title
        assert array.attrs['CLASS'] == 'VLARRAY'
        assert array.attrs['dtype'] == np.dtype(dtype).name

        array.append(np.array([10, 12, 15]))
        assert isinstance(array[-1], np.ndarray)
        assert np.all(array[-1] == np.array([10, 12, 15]))

        array.append(np.array([10, 4, 2, 4, 6, 4]))
        assert np.all(array[-1] == [10, 4, 2, 4, 6, 4])

    def test_vlarray_string(self, get_backend):
        bck = get_backend
        g1 = bck.get_set_group(bck.root(), 'g1')
        title = 'this is a vlarray'
        dtype = 'string'
        sarray = bck.create_vlarray(g1, 'array', dtype=dtype, title=title)
        assert sarray.attrs['TITLE'] == title
        assert sarray.attrs['CLASS'] == 'VLARRAY'
        assert sarray.attrs['dtype'] == np.dtype(np.uint8).name
        assert sarray.attrs['subdtype'] == 'string'
        st = 'this is a string'
        st2 = 'this is a second string'
        assert sarray.array_to_string(sarray.string_to_array(st)) == st

        sarray.append(st)
        assert sarray[-1] == st

        sarray.append(st2)
        assert sarray[-1] == st2


class TestGroup:

    def test_children(self, get_backend):
        bck = get_backend
        title = lambda x: f'this is a {x} group'
        group = bck.add_group('base group', 'scan', bck.root(), title='base group')

        n1 = bck.create_carray(group, name='n1', obj=np.zeros((5, 2)), title=title('n1'))
        n2 = bck.add_group('n2', 'scan', group, title=title('n2'))

        assert isinstance(group, backends.GROUP)
        assert group.children_name() == ['N2', 'n1']  # notice the capital for the groups...
        n3 = bck.add_group('m1', 'scan', group, title=title('n2'))
        assert group.children_name() == ['M1', 'N2', 'n1']  # notice the capital for the groups... and the sorted

        for child_name in list(group.children().keys()):
            assert child_name in group.children_name()
        for child in list(group.children().values()):
            assert child in [n1, n2, n3]

    def test_remove_children(self, get_backend):
        bck = get_backend
        title = lambda x: f'this is a {x} group'
        group = bck.add_group('base group', 'scan', bck.root(), title='base group')

        n1 = bck.create_carray(group, name='n1', obj=np.zeros((5, 2)), title=title('n1'))
        n2 = bck.add_group('n2', 'scan', group, title=title('n2'))

        group.remove_children()
        assert group.children_name() == []  # notice the capital for the groups...
