# -*- coding: utf-8 -*-
"""Tests of the events sent when an extension starts and ends a run"""
import dataclasses
from datetime import datetime

import pytest

from pymodaq_data.h5modules.run_events import RunEvents, RunInfo


@pytest.fixture(autouse=True)
def clean_registry():
    yield
    for name in RunEvents.names():
        RunEvents.unregister(name)


def test_registry_cannot_be_instantiated():
    with pytest.raises(TypeError):
        RunEvents()


def test_run_info_is_immutable():
    info = RunInfo(extension='MyScan')
    with pytest.raises(dataclasses.FrozenInstanceError):
        info.extension = 'other'


def test_times_have_an_offset_to_utc():
    info = RunInfo(extension='MyScan')
    assert datetime.fromisoformat(info.started_at).utcoffset() is not None
    assert datetime.fromisoformat(info.ended().ended_at).utcoffset() is not None


def test_ended_keeps_the_run_and_adds_its_end():
    info = RunInfo(extension='MyScan', payload={'a': 1})
    ended = info.ended()

    assert info.ended_at is None  # the first one is not modified
    assert ended.run_id == info.run_id
    assert ended.started_at == info.started_at
    assert ended.payload == {'a': 1}


def test_actions_are_called_in_each_event():
    calls = []
    RunEvents.register('a', on_started=lambda i: calls.append('a started'), on_ended=lambda i: calls.append('a ended'))
    RunEvents.register('b', on_ended=lambda i: calls.append('b ended'))
    info = RunInfo(extension='MyScan')

    RunEvents.notify_started(info)
    RunEvents.notify_ended(info)

    assert calls == ['a started', 'a ended', 'b ended']


def test_failing_action_does_not_stop_the_others():
    calls = []
    RunEvents.register('bad', on_started=lambda i: 1 / 0)
    RunEvents.register('good', on_started=calls.append)
    info = RunInfo(extension='MyScan')

    RunEvents.notify_started(info)

    assert calls == [info]


def test_unregister():
    RunEvents.register('a', on_started=print)
    RunEvents.unregister('a')
    RunEvents.unregister('a')  # unknown names are ignored
    assert RunEvents.names() == []


class TestPayload:
    def test_payload_cannot_be_modified(self):
        info = RunInfo(extension='MyScan', payload={'scan_type': 'Scan1D'})
        with pytest.raises(TypeError):
            info.payload['scan_type'] = 'other'

    def test_payload_is_a_copy(self):
        payload = {'scan_type': 'Scan1D', 'detectors': ['a', 'b']}
        info = RunInfo(extension='MyScan', payload=payload)

        payload['scan_type'] = 'other'
        payload['detectors'].append('c')

        assert info.payload['scan_type'] == 'Scan1D'
        assert info.payload['detectors'] == ('a', 'b')

    def test_nested_values_cannot_be_modified(self):
        info = RunInfo(extension='MyScan', payload={'nested': {'a': [1, 2]}})

        with pytest.raises(TypeError):
            info.payload['nested']['a'] = 3
        assert info.payload['nested']['a'] == (1, 2)

    def test_ended_run_keeps_the_payload(self):
        info = RunInfo(extension='MyScan', payload={'a': {'b': 1}})
        assert dict(info.ended().payload['a']) == {'b': 1}
