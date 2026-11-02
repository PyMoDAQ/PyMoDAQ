"""The list of files opened in the editor is cached in a file of the config folder: reading it must never
run code, and the caches written by older versions must still be read.
"""
import json
import pickle
from pathlib import Path

import pytest

from pymodaq_gui.editor.monaco import read_files_cache, write_files_cache
import warnings

from pymodaq_utils.safe_pickle import UnsafePickleError, LegacyFormatWarning

TRIGGERED = []


def _trigger():
    TRIGGERED.append(True)


class _InertPayload:
    def __reduce__(self):
        return _trigger, ()


def test_unsafe_legacy_cache_is_refused_and_not_run(tmp_path):
    TRIGGERED.clear()
    cache = tmp_path / 'monaco_files'
    cache.write_bytes(pickle.dumps(_InertPayload()))

    with pytest.raises(UnsafePickleError):
        read_files_cache(cache)

    assert TRIGGERED == []


def test_legacy_pickled_cache_is_still_read(tmp_path):
    files = [Path('/some/where/a.py'), Path('b.py')]
    cache = tmp_path / 'monaco_files'
    cache.write_bytes(pickle.dumps(files))

    assert read_files_cache(cache) == files


def test_empty_legacy_cache_is_still_read(tmp_path):
    cache = tmp_path / 'monaco_files'
    cache.write_bytes(pickle.dumps([]))

    assert read_files_cache(cache) == []


def test_cache_round_trip(tmp_path):
    files = [tmp_path / 'a.py', Path('b with spaces.py'), Path('héllo.py')]
    cache = tmp_path / 'monaco_files'

    write_files_cache(files, cache)

    assert read_files_cache(cache) == files


def test_new_cache_is_plain_json(tmp_path):
    cache = tmp_path / 'monaco_files'
    write_files_cache([Path('a.py')], cache)

    with open(cache, 'rb') as f:
        assert json.load(f) == ['a.py']


def test_reading_a_legacy_cache_warns_that_the_file_should_be_migrated(tmp_path):
    cache = tmp_path / 'monaco_files'
    cache.write_bytes(pickle.dumps([Path('a.py')]))

    with pytest.warns(LegacyFormatWarning, match='migrate'):
        read_files_cache(cache)


def test_reading_a_new_cache_does_not_warn(tmp_path):
    cache = tmp_path / 'monaco_files'
    write_files_cache([Path('a.py')], cache)

    with warnings.catch_warnings():
        warnings.simplefilter('error', LegacyFormatWarning)
        read_files_cache(cache)
