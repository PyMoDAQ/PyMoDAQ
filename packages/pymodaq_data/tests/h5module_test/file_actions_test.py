# -*- coding: utf-8 -*-
"""Tests of the actions run when a file written with a backend is opened or closed"""
import dataclasses
from pathlib import Path

import pytest

from pymodaq_data.h5modules import backends
from pymodaq_data.h5modules.file_actions import FileAction, FileActions

tested_backend = [b for b in ['tables', 'h5py'] if b in backends.backends_available]


@pytest.fixture(params=tested_backend)
def backend_name(request):
    return request.param


@pytest.fixture
def events():
    """Register an action recording the events and removes it afterwards"""
    recorded = []
    FileActions.register('recorder',
                         on_opened=lambda path: recorded.append(('opened', path)),
                         on_closed=lambda path: recorded.append(('closed', path)))
    yield recorded
    FileActions.unregister('recorder')


def test_registry():
    FileActions.register('some_action', on_closed=lambda path: None)
    assert 'some_action' in FileActions.names()
    FileActions.unregister('some_action')
    assert 'some_action' not in FileActions.names()
    FileActions.unregister('some_action')  # unknown names are ignored


def test_failing_action_does_not_stop_the_others(events):
    def failing(path):
        raise RuntimeError('boom')

    FileActions.register('failing', on_closed=failing)
    try:
        FileActions.notify_closed(Path('a.h5'))
    finally:
        FileActions.unregister('failing')
    assert events == [('closed', Path('a.h5'))]


def test_written_file_is_notified_once_when_closed(backend_name, tmp_path, events):
    path = tmp_path / 'file.h5'
    bck = backends.H5Backend(backend_name)
    bck.open_file(path, 'w')
    assert events == [('opened', path)]
    bck.close_file()
    assert events == [('opened', path), ('closed', path)]
    bck.close_file()  # closing a closed file is not a new event
    assert len(events) == 2


def test_file_opened_to_read_is_not_notified(backend_name, tmp_path, events):
    path = tmp_path / 'file.h5'
    bck = backends.H5Backend(backend_name)
    bck.open_file(path, 'w')
    bck.close_file()
    events.clear()

    reader = backends.H5Backend(backend_name)
    reader.open_file(path, 'r')
    reader.close_file()
    assert events == []


def test_file_kept_open_is_not_notified_as_closed(tmp_path, events):
    if 'h5py' not in backends.backends_available:
        pytest.skip('h5py is needed for SWMR')
    path = tmp_path / 'file.h5'
    bck = backends.H5Backend('h5py')
    bck.open_file(path, 'w', swmr_mode=True)
    bck._swmr_enabled = True
    bck.finalize_swmr(keep_open=True)
    assert ('closed', path) not in events
    assert bck.isopen()
    bck.close_file()
    assert events[-1] == ('closed', path)


def test_registry_cannot_be_instantiated():
    with pytest.raises(TypeError):
        FileActions()


def test_file_action_is_immutable():
    action = FileAction(on_closed=print)
    with pytest.raises(dataclasses.FrozenInstanceError):
        action.on_closed = None
