# -*- coding: utf-8 -*-
"""Tests of the events sent when an extension starts and ends a saving"""
import dataclasses
from datetime import datetime

import pytest

from pymodaq_data.h5modules.ext_saving_events import ExtSavingEvents, ExtSavingInfo


@pytest.fixture(autouse=True)
def clean_registry():
    yield
    for name in ExtSavingEvents.names():
        ExtSavingEvents.unregister(name)


def test_registry_cannot_be_instantiated():
    with pytest.raises(TypeError):
        ExtSavingEvents()


def test_saving_info_is_immutable():
    info = ExtSavingInfo(extension='MyScan')
    with pytest.raises(dataclasses.FrozenInstanceError):
        info.extension = 'other'


def test_times_have_an_offset_to_utc():
    info = ExtSavingInfo(extension='MyScan')
    assert datetime.fromisoformat(info.started_at).utcoffset() is not None
    assert datetime.fromisoformat(info.ended().ended_at).utcoffset() is not None


def test_ended_keeps_the_saving_and_adds_its_end():
    info = ExtSavingInfo(extension='MyScan', payload={'a': 1})
    ended = info.ended()

    assert info.ended_at is None  # the first one is not modified
    assert ended.saving_id == info.saving_id
    assert ended.started_at == info.started_at
    assert ended.payload == {'a': 1}


def test_actions_are_called_in_each_event():
    calls = []
    ExtSavingEvents.register('a', on_started=lambda i: calls.append('a started'), on_ended=lambda i: calls.append('a ended'))
    ExtSavingEvents.register('b', on_ended=lambda i: calls.append('b ended'))
    info = ExtSavingInfo(extension='MyScan')

    ExtSavingEvents.notify_started(info)
    ExtSavingEvents.notify_ended(info)

    assert calls == ['a started', 'a ended', 'b ended']


def test_failing_action_does_not_stop_the_others():
    calls = []
    ExtSavingEvents.register('bad', on_started=lambda i: 1 / 0)
    ExtSavingEvents.register('good', on_started=calls.append)
    info = ExtSavingInfo(extension='MyScan')

    ExtSavingEvents.notify_started(info)

    assert calls == [info]


def test_unregister():
    ExtSavingEvents.register('a', on_started=print)
    ExtSavingEvents.unregister('a')
    ExtSavingEvents.unregister('a')  # unknown names are ignored
    assert ExtSavingEvents.names() == []


class TestPayload:
    def test_payload_cannot_be_modified(self):
        info = ExtSavingInfo(extension='MyScan', payload={'scan_type': 'Scan1D'})
        with pytest.raises(TypeError):
            info.payload['scan_type'] = 'other'

    def test_payload_is_a_copy(self):
        payload = {'scan_type': 'Scan1D', 'detectors': ['a', 'b']}
        info = ExtSavingInfo(extension='MyScan', payload=payload)

        payload['scan_type'] = 'other'
        payload['detectors'].append('c')

        assert info.payload['scan_type'] == 'Scan1D'
        assert info.payload['detectors'] == ('a', 'b')

    def test_nested_values_cannot_be_modified(self):
        info = ExtSavingInfo(extension='MyScan', payload={'nested': {'a': [1, 2]}})

        with pytest.raises(TypeError):
            info.payload['nested']['a'] = 3
        assert info.payload['nested']['a'] == (1, 2)

    def test_ended_saving_keeps_the_payload(self):
        info = ExtSavingInfo(extension='MyScan', payload={'a': {'b': 1}})
        assert dict(info.ended().payload['a']) == {'b': 1}
