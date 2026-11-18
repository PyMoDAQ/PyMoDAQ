"""Attributes of hdf5 nodes can come from any file: reading them must never run code."""
import datetime
import json
from pathlib import Path

import numpy as np
import pytest

from pymodaq_data.h5modules import backends

tested_backend = [b for b in ['tables', 'h5py'] if b in backends.backends_available]


@pytest.fixture(params=tested_backend)
def group(request, tmp_path):
    bck = backends.H5Backend(request.param)
    bck.open_file(tmp_path.joinpath('h5file.h5'), 'w', 'test file')
    yield bck.get_set_group(bck.root(), 'g1')
    bck.close_file()


def _write_raw_attribute(group, name, raw: str):
    """Write the attribute as a foreign file would, bypassing JsonConverter"""
    if group.backend == 'tables':
        group.node._v_attrs[name] = raw
    else:
        group.node.attrs[name] = raw


@pytest.mark.parametrize('value', [
    10, 2.5, 'a text', True, b'bytes', (1, 'a'), [1, 2, 3], datetime.datetime(2020, 5, 24, 10, 52, 55),
    datetime.date(2020, 5, 24), np.float64(2.5), np.float32(0.1), np.int32(-3), np.uint16(7), np.bool_(True),
    1 + 2j, {1, 'a'}, frozenset({2}), Path('/some/file.h5'), {'a': [1, 2.5]},
])
def test_attributes_round_trip(group, value):
    group.attrs['my_attribute'] = value

    assert group.attrs['my_attribute'] == value
    assert group.attrs.to_dict()['my_attribute'] == value


def test_unsafe_attribute_is_not_evaluated(group):
    stored = json.dumps(dict(module='builtins', type='str', data="__import__('sys').version"))
    _write_raw_attribute(group, 'my_attribute', stored)

    assert group.attrs['my_attribute'] == json.loads(stored)
    assert group.attrs.to_dict()['my_attribute'] == json.loads(stored)


@pytest.mark.parametrize('array', [np.arange(1500.) / 7, np.array([[1, 2], [3, 4]], dtype=np.int16),
                                   np.array(['a', 'bc'])])
# more than the 1000 values numpy shows in a repr, below the 64 kB of an attribute with PyTables
def test_array_attribute_round_trip(group, array):
    group.attrs['my_attribute'] = array
    result = group.attrs['my_attribute']

    assert result.dtype == array.dtype and np.array_equal(result, array)


def test_attribute_of_unsupported_type_warns(group):
    with pytest.warns(UserWarning, match='object'):
        group.attrs['my_attribute'] = object()
