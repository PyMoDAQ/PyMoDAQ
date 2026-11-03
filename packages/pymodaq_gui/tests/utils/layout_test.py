"""Dock layouts are loaded from files that can be exchanged: loading one must never run code.

The payloads below are inert: the only thing they try to do is append to TRIGGERED.
"""
import json
import pickle

import pytest
from pyqtgraph.dockarea import DockArea, Dock

from pymodaq_gui.utils import layout
import warnings

from pymodaq_utils.safe_pickle import UnsafePickleError, LegacyFormatWarning

TRIGGERED = []


def _trigger():
    TRIGGERED.append(True)


class _InertPayload:
    def __reduce__(self):
        return _trigger, ()


def make_dockarea(qtbot, arrangement='right') -> DockArea:
    area = DockArea()
    qtbot.addWidget(area)
    d1 = Dock('dock1', size=(100, 100))
    d2 = Dock('dock2', size=(200, 100))
    d3 = Dock('dock3', size=(100, 50))
    area.addDock(d1, 'left')
    area.addDock(d2, arrangement, d1)
    area.addDock(d3, 'bottom', d2)
    return area


def test_unsafe_legacy_layout_is_refused_and_not_run(qtbot, tmp_path):
    TRIGGERED.clear()
    file = tmp_path / 'unsafe.dock'
    file.write_bytes(pickle.dumps(_InertPayload()))

    with pytest.raises(UnsafePickleError):
        layout.load_layout_state(make_dockarea(qtbot), file)

    assert TRIGGERED == []


def test_legacy_pickled_layout_is_still_loaded(qtbot, tmp_path):
    reference = make_dockarea(qtbot)
    file = tmp_path / 'legacy.dock'
    with open(file, 'wb') as f:
        pickle.dump(reference.saveState(), f, pickle.HIGHEST_PROTOCOL)

    other = make_dockarea(qtbot, arrangement='bottom')
    assert json.dumps(other.saveState()) != json.dumps(reference.saveState())

    layout.load_layout_state(other, file)

    assert json.dumps(other.saveState()) == json.dumps(reference.saveState())


def test_layout_round_trip(qtbot, tmp_path):
    reference = make_dockarea(qtbot)
    file = tmp_path / 'new.dock'
    layout.save_layout_state(reference, file)

    other = make_dockarea(qtbot, arrangement='bottom')
    layout.load_layout_state(other, file)

    assert json.dumps(other.saveState()) == json.dumps(reference.saveState())


def test_new_layout_files_are_plain_json(qtbot, tmp_path):
    file = tmp_path / 'new.dock'
    layout.save_layout_state(make_dockarea(qtbot), file)

    with open(file, 'rb') as f:
        content = json.load(f)

    assert 'main' in content


def test_loading_a_legacy_layout_warns_that_the_file_should_be_migrated(qtbot, tmp_path):
    file = tmp_path / 'legacy.dock'
    with open(file, 'wb') as f:
        pickle.dump(make_dockarea(qtbot).saveState(), f, pickle.HIGHEST_PROTOCOL)

    with pytest.warns(LegacyFormatWarning, match='migrate'):
        layout.load_layout_state(make_dockarea(qtbot), file)


def test_loading_a_new_layout_does_not_warn(qtbot, tmp_path):
    file = tmp_path / 'new.dock'
    layout.save_layout_state(make_dockarea(qtbot), file)

    with warnings.catch_warnings():
        warnings.simplefilter('error', LegacyFormatWarning)
        layout.load_layout_state(make_dockarea(qtbot), file)
