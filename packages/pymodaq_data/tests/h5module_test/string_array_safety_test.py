"""Strings stored in .h5 files must never be able to run code when read back.

The payloads below are inert: the only thing they try to do is append to TRIGGERED.
"""
import pickle

import numpy as np
import pytest

from pymodaq_data.h5modules import backends
from pymodaq_utils.safe_pickle import UnsafePickleError

tested_backend = [b for b in ['tables', 'h5py'] if b in backends.backends_available]

TRIGGERED = []


def _trigger():
    TRIGGERED.append(True)


class _InertPayload:
    def __reduce__(self):
        return _trigger, ()


@pytest.fixture(params=tested_backend)
def string_array(request, tmp_path):
    bck = backends.H5Backend(request.param)
    bck.open_file(tmp_path.joinpath('h5file.h5'), 'w', 'test file')
    group = bck.get_set_group(bck.root(), 'g1')
    yield bck.create_vlarray(group, 'strings', dtype='string', title='strings')
    bck.close_file()


def _append_raw(string_array, raw: bytes):
    """Write raw bytes in the node, bypassing StringARRAY.append, as a foreign file would"""
    backends.VLARRAY.append(string_array, np.frombuffer(raw, np.uint8))


def test_unsafe_legacy_content_is_refused_and_not_run(string_array):
    TRIGGERED.clear()
    _append_raw(string_array, pickle.dumps(_InertPayload()))

    with pytest.raises(UnsafePickleError):
        string_array.read()
    with pytest.raises(UnsafePickleError):
        string_array[0]

    assert TRIGGERED == []


@pytest.mark.parametrize('text', ['this is a string', '', 'héllo wörld, 温度 (°C)', 'line1\nline2'])
def test_legacy_pickled_strings_are_still_readable(string_array, text):
    for protocol in (2, 4, pickle.HIGHEST_PROTOCOL):
        _append_raw(string_array, pickle.dumps(text, protocol=protocol))

    assert string_array.read() == [text] * 3
    assert string_array[0] == text


@pytest.mark.parametrize('text', ['this is a string', '', 'héllo wörld, 温度 (°C)', 'line1\nline2'])
def test_new_strings_round_trip(string_array, text):
    string_array.append(text)
    string_array.append(text + '!')

    assert string_array[0] == text
    assert string_array.read() == [text, text + '!']


def test_new_strings_are_stored_as_plain_utf8(string_array):
    string_array.append('héllo')

    raw = bytes(backends.VLARRAY.read(string_array)[0])
    assert raw == 'héllo'.encode('utf-8')
