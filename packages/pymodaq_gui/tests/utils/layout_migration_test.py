"""Migrating a layout file written by an older version gives a json file and leaves the original untouched."""
import json
import pickle

import pytest

from pymodaq_gui.utils import layout
from pymodaq_utils.safe_pickle import UnsafePickleError

TRIGGERED = []


def _trigger():
    TRIGGERED.append(True)


class _InertPayload:
    def __reduce__(self):
        return _trigger, ()


STATE = {'main': ('vertical', [], {'sizes': [10, 20]}), 'float': []}


def test_legacy_layout_is_migrated_to_json(tmp_path):
    source = tmp_path / 'legacy.dock'
    source.write_bytes(pickle.dumps(STATE, pickle.HIGHEST_PROTOCOL))
    before = source.read_bytes()

    destination = layout.migrate_layout_file(source)

    assert destination == tmp_path / 'legacy_migrated.dock'
    assert source.read_bytes() == before
    assert json.loads(destination.read_text(encoding='utf-8')) == json.loads(json.dumps(STATE))


def test_migrating_does_not_overwrite(tmp_path):
    source = tmp_path / 'legacy.dock'
    source.write_bytes(pickle.dumps(STATE))
    destination = tmp_path / 'there.dock'
    destination.write_text('precious')

    with pytest.raises(FileExistsError):
        layout.migrate_layout_file(source, destination)

    assert destination.read_text() == 'precious'


def test_doubtful_layout_is_refused_without_running_anything(tmp_path):
    TRIGGERED.clear()
    source = tmp_path / 'doubtful.dock'
    source.write_bytes(pickle.dumps(_InertPayload()))

    with pytest.raises(UnsafePickleError):
        layout.migrate_layout_file(source)

    assert TRIGGERED == []
    assert not (tmp_path / 'doubtful_migrated.dock').exists()
