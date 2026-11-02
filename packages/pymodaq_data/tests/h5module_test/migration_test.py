"""Migrating a file written by an older version must give a file without pickled content, leave the original
file untouched, and never run what a doubtful file contains.
"""
import hashlib
import pickle
import warnings

import numpy as np
import pytest

from pymodaq_data.h5modules import backends
from pymodaq_data.h5modules.migration import migrate_h5_file
from pymodaq_utils.safe_pickle import UnsafePickleError, LegacyFormatWarning

tested_backend = [b for b in ['tables', 'h5py'] if b in backends.backends_available]

TRIGGERED = []


def _trigger():
    TRIGGERED.append(True)


class _InertPayload:
    def __reduce__(self):
        return _trigger, ()


def sha(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_legacy_file(path, backend, legacy_strings=('first', 'héllo 温度'), extra_raw=()):
    """A file as an older version wrote it: strings are stored as pickles"""
    bck = backends.H5Backend(backend)
    bck.open_file(path, 'w', 'legacy file')
    group = bck.get_set_group(bck.root(), 'g1')
    strings = bck.create_vlarray(group, 'logger', dtype='string', title='logger')
    for text in legacy_strings:
        backends.VLARRAY.append(strings, np.frombuffer(pickle.dumps(text), np.uint8))
    for raw in extra_raw:
        backends.VLARRAY.append(strings, np.frombuffer(raw, np.uint8))
    other = bck.create_vlarray(group, 'other_strings', dtype='string', title='other')
    other.append('already new')
    bck.create_carray(group, 'numbers', np.array([1., 2., 3.]), title='numbers')
    bck.close_file()


def read_strings(path, backend):
    bck = backends.H5Backend(backend)
    bck.open_file(path, 'r')
    try:
        return (bck.get_node('/g1/logger').read(), bck.get_node('/g1/other_strings').read(),
                np.array(bck.get_node('/g1/numbers').read()))
    finally:
        bck.close_file()


@pytest.mark.parametrize('backend', tested_backend)
def test_migrated_file_has_the_same_content_without_pickle(tmp_path, backend):
    source = tmp_path / 'legacy.h5'
    make_legacy_file(source, backend)
    before = sha(source)

    destination, nodes = migrate_h5_file(source)

    assert destination == tmp_path / 'legacy_migrated.h5'
    assert nodes == 1
    assert sha(source) == before  # the original file is not touched
    with warnings.catch_warnings():
        warnings.simplefilter('error', LegacyFormatWarning)  # nothing legacy is left
        logger, other, numbers = read_strings(destination, 'h5py')
    assert logger == ['first', 'héllo 温度']
    assert other == ['already new']
    assert np.allclose(numbers, [1., 2., 3.])


@pytest.mark.parametrize('backend', tested_backend)
def test_migrating_a_migrated_file_has_nothing_to_do(tmp_path, backend):
    source = tmp_path / 'legacy.h5'
    make_legacy_file(source, backend)
    migrated, _ = migrate_h5_file(source)

    _, nodes = migrate_h5_file(migrated, tmp_path / 'again.h5')

    assert nodes == 0


def test_an_existing_destination_is_not_overwritten(tmp_path):
    source = tmp_path / 'legacy.h5'
    make_legacy_file(source, tested_backend[0])
    destination = tmp_path / 'already_there.h5'
    destination.write_bytes(b'precious')

    with pytest.raises(FileExistsError):
        migrate_h5_file(source, destination)

    assert destination.read_bytes() == b'precious'


@pytest.mark.parametrize('backend', tested_backend)
def test_a_doubtful_file_is_refused_without_running_anything(tmp_path, backend):
    TRIGGERED.clear()
    source = tmp_path / 'doubtful.h5'
    make_legacy_file(source, backend, extra_raw=[pickle.dumps(_InertPayload())])

    with pytest.raises(UnsafePickleError):
        migrate_h5_file(source)

    assert TRIGGERED == []
    assert not (tmp_path / 'doubtful_migrated.h5').exists()
