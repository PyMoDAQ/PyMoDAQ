# -*- coding: utf-8 -*-
"""
Created the 23/11/2022

@author: Sebastien Weber
"""

from datetime import datetime

import numpy as np
import pytest

from pymodaq_data.h5modules.saving import H5SaverLowLevel
from pymodaq_data.h5modules import backends
from pymodaq_data.h5modules.file_actions import FileActions
from pymodaq_data.h5modules.ext_saving_events import ExtSavingEvents
from pymodaq.utils.h5modules.module_saving import DetectorSaver, ScanSaver, GroupModuleType, TimeModuleSaver

from pymodaq_gui.parameter import Parameter
from pymodaq.control_modules.mocks import MockScan, MockDAQMove, MockDAQViewer

tested_backend = [b for b in ['tables', 'h5py'] if b in backends.backends_available]


@pytest.fixture(params=tested_backend)
def h5saver_with_settings(request, tmp_path):
    h5saver = H5SaverLowLevel(backend=request.param)
    addhoc_file_path = tmp_path.joinpath('h5file.h5')
    h5saver.init_file(file_name=addhoc_file_path)
    params = [{'title': 'mysaver', 'name': 'saver', 'type': 'str', 'value': 'myh5saver'}]
    h5saver.settings = Parameter.create(name='settings', type='group', children=params)  # create a Parameter
    yield h5saver
    h5saver.close_file()


class TestDetectorSaver:
    def test_get_set_node(self, h5saver_with_settings):
        h5saver = h5saver_with_settings
        mock_det = MockDAQViewer(h5saver)
        det_saver = DetectorSaver(module=mock_det)
        det_saver.h5saver = h5saver

        assert det_saver.group_type == GroupModuleType.DETECTOR

        for node in h5saver.walk_nodes('/'):
            assert 'detector' not in node.attrs

        node0 = det_saver.get_set_node()
        assert node0.attrs['TITLE'] == 'MyDet0D'
        assert node0.title == 'MyDet0D'
        assert node0.name == 'Detector000'

        node1 = det_saver.get_set_node()
        assert node1 == node0


class TestScanSaver:
    def test_get_set_node(self, h5saver_with_settings):
        h5saver = h5saver_with_settings
        mock_scan_module = MockScan(h5saver)
        scan_saver = ScanSaver(module=mock_scan_module)
        scan_saver.h5saver = h5saver

        assert scan_saver.group_type == GroupModuleType.SCAN

        for node in h5saver.walk_nodes('/'):
            assert 'scan' not in node.attrs

        node0 = scan_saver.get_set_node()
        assert node0.attrs['TITLE'] == 'MyScan'
        assert node0.title == 'MyScan'
        assert node0.name == 'Scan000'
        assert len(node0.children_name())-1 == len(mock_scan_module.modules_manager.modules_all)  # -1 because of the Timestamps node
        assert node0.children_name() == ['Actuator000', 'Detector000', 'Detector001', 'Timestamps']
        assert node0.get_child('Actuator000').title == 'MyAct'

        node1 = scan_saver.get_set_node()
        assert node1 == node0

        node2 = scan_saver.get_set_node(new=True)
        assert node2 != node0
        assert node2.name == 'Scan001'
        assert node2.children_name() == ['Actuator000', 'Detector000', 'Detector001', 'Timestamps']
        assert node2.get_child('Actuator000').title == 'MyAct'

        node3 = scan_saver.get_set_node()
        assert node3 == node2


class TestExtensionSaverFinalize:
    """Regression tests for GH issue #1477: current_nodes is a long-lived cache
    ExtensionSaver.add_data reuses across calls (unlike DetectorSaver/ActuatorSaver,
    which refetch their node from raw_group on every add_data), so it must be
    refreshed after finalize(keep_open=True) ends an SWMR session, or the next
    add_data reuses a Node tied to the file instance that was just closed and
    reopened."""

    def test_finalize_never_reads_cached_nodes_without_swmr(self, h5saver_with_settings, monkeypatch):
        """Regression for a real CI failure (tables backend): finalize() used to
        read current_nodes/module_group/time_saver paths unconditionally to decide
        whether to refresh them, even when there was nothing to refresh (SWMR never
        active, e.g. the tables backend never activates it). On tables, reading
        .path off a node from a closed/previous session raises ClosedNodeError;
        h5py returns None instead, masking the bug - make .path always raise here
        to catch a regression under either backend.
        """
        h5saver = h5saver_with_settings
        mock_scan_module = MockScan(h5saver)
        scan_saver = ScanSaver(module=mock_scan_module)
        scan_saver.h5saver = h5saver
        scan_saver.get_set_node()

        def raise_if_read(self):
            raise AssertionError('a cached node path was read without SWMR ever being active')

        monkeypatch.setattr(backends.GROUP, 'path', property(raise_if_read))

        scan_saver.finalize(keep_open=True)  # no SWMR ever enabled: nothing to refresh
        scan_saver.finalize(keep_open=False)

    @pytest.mark.skipif('h5py' not in tested_backend, reason='h5py not available')
    def test_current_nodes_refreshed_after_finalize_keep_open(self, tmp_path):
        h5saver = H5SaverLowLevel(backend='h5py')
        h5saver.init_file(file_name=tmp_path.joinpath('scan_finalize.h5'), swmr_mode=True)
        h5saver.settings = Parameter.create(
            name='settings', type='group',
            children=[{'title': 'mysaver', 'name': 'saver', 'type': 'str', 'value': 'myh5saver'}])

        mock_scan_module = MockScan(h5saver)
        scan_saver = ScanSaver(module=mock_scan_module)
        scan_saver.h5saver = h5saver
        scan_saver.get_set_node()

        stale_nodes = dict(scan_saver.current_nodes)
        assert stale_nodes  # sanity: detectors/actuators were populated
        stale_time_group = scan_saver._time_saver._module_group
        assert stale_time_group is not None

        h5saver.flush()
        h5saver.enable_swmr()
        assert h5saver.is_swmr_active

        scan_saver.finalize(keep_open=True)
        assert not h5saver.is_swmr_active
        assert h5saver.isopen()

        for name, node in scan_saver.current_nodes.items():
            # refreshed: a new Node, not the one fetched before the pause
            assert node.node != stale_nodes[name].node
            # and usable: must not raise on a node tied to the closed file object
            assert node.attrs['TITLE']

        # _time_saver's own module_group, reused by every add_time, must be
        # refreshed too
        assert scan_saver._time_saver._module_group.node != stale_time_group.node
        assert scan_saver._time_saver._module_group.attrs['TITLE']

        with pytest.raises(Exception):
            stale_nodes[next(iter(stale_nodes))].attrs['TITLE']
        with pytest.raises(Exception):
            stale_time_group.attrs['TITLE']

        h5saver.close_file()


class TestTimeModuleSaver:
    def test_timestamps_initialized_with_nan(self, h5saver_with_settings):
        """All unwritten positions of the timestamp array are NaN."""
        h5saver = h5saver_with_settings
        ts_saver = TimeModuleSaver()
        ts_saver.h5saver = h5saver

        scan_group = h5saver.get_set_group(h5saver.raw_group, 'Scan000')
        ts_saver.get_set_node(scan_group)

        EXT_SHAPE = (4,)
        ts_saver.initialize(EXT_SHAPE)
        # Trigger array creation by writing one point
        ts_saver.add_time((0,))

        node = h5saver.get_node('/RawData/Scan000/Timestamps/Data0D/CH00/Data00')
        arr = node.read()
        assert arr.shape == EXT_SHAPE
        # Index 0 was written (finite); indices 1-3 must be NaN
        assert np.isfinite(arr[0])
        assert np.all(np.isnan(arr[1:]))

    def test_timestamps_written_value(self, h5saver_with_settings):
        """Written timestamp is finite and at the correct index; unwritten stay NaN."""
        h5saver = h5saver_with_settings
        ts_saver = TimeModuleSaver()
        ts_saver.h5saver = h5saver

        scan_group = h5saver.get_set_group(h5saver.raw_group, 'Scan000')
        ts_saver.get_set_node(scan_group)

        EXT_SHAPE = (5,)
        ts_saver.initialize(EXT_SHAPE)

        ts_saver.add_time((2,))

        node = h5saver.get_node('/RawData/Scan000/Timestamps/Data0D/CH00/Data00')
        arr = node.read()
        assert np.isfinite(arr[2])
        assert arr[2] >= 0.0
        assert np.isnan(arr[0])
        assert np.isnan(arr[1])
        assert np.isnan(arr[3])
        assert np.isnan(arr[4])

    def test_timestamps_multiple_writes(self, h5saver_with_settings):
        """Multiple writes populate the correct positions; unvisited stay NaN."""
        h5saver = h5saver_with_settings
        ts_saver = TimeModuleSaver()
        ts_saver.h5saver = h5saver

        scan_group = h5saver.get_set_group(h5saver.raw_group, 'Scan000')
        ts_saver.get_set_node(scan_group)

        EXT_SHAPE = (6,)
        ts_saver.initialize(EXT_SHAPE)

        for idx in [1, 3, 5]:
            ts_saver.add_time((idx,))

        node = h5saver.get_node('/RawData/Scan000/Timestamps/Data0D/CH00/Data00')
        arr = node.read()
        for idx in [1, 3, 5]:
            assert np.isfinite(arr[idx])
            assert arr[idx] >= 0.0
        for idx in [0, 2, 4]:
            assert np.isnan(arr[idx])



class TestExtSavingEvents:
    """The extension savers tell the ExtSavingEvents registry when a saving starts and when it ends"""

    @pytest.fixture
    def events(self):
        received = []
        ExtSavingEvents.register('test', on_started=lambda info: received.append(('started', info)),
                           on_ended=lambda info: received.append(('ended', info)))
        yield received
        ExtSavingEvents.unregister('test')

    @pytest.fixture
    def scan_saver(self, h5saver_with_settings):
        module = MockScan(h5saver_with_settings)
        module.saving_payload = lambda: {'scan_type': 'Scan1D'}
        saver = ScanSaver(module=module)
        saver.h5saver = h5saver_with_settings
        return saver

    def test_saving_starts_with_a_new_group_only(self, scan_saver, events):
        scan_saver.get_set_node()  # creates the first group: a saving starts
        scan_saver.get_set_node()  # gets it back: no new saving
        scan_saver.get_set_node(new=True)

        assert [name for name, _ in events] == ['started', 'started']

    def test_started_saving_gives_what_is_known(self, scan_saver, events):
        scan_saver.get_set_node()

        info = events[0][1]
        assert info.extension == 'MyScan'
        assert dict(info.payload) == {'scan_type': 'Scan1D'}
        assert info.h5_path.name == 'h5file.h5'
        assert info.ended_at is None
        assert datetime.fromisoformat(info.started_at).utcoffset() is not None  # the offset to UTC is given

    def test_ended_saving_is_the_started_one_with_its_end(self, scan_saver, events):
        scan_saver.get_set_node()
        scan_saver.end_saving()

        started, ended = events[0][1], events[1][1]
        assert events[1][0] == 'ended'
        assert ended.saving_id == started.saving_id
        assert ended.ended_at is not None
        assert scan_saver.saving is None  # no saving is going on any more

    def test_ending_without_saving_does_nothing(self, scan_saver, events):
        scan_saver.end_saving()
        assert events == []

    def test_snapshot_is_announced_as_a_closed_file(self, scan_saver, events):
        closed = []
        FileActions.register('test_png', on_closed=closed.append)
        try:
            scan_saver.get_set_node()
            path = scan_saver.snapshot_file_path()
            scan_saver.end_saving(path)
        finally:
            FileActions.unregister('test_png')

        assert path.suffix == '.png'
        assert closed == [path]
        assert events[1][1].snapshot_path == path

    def test_failing_payload_does_not_stop_the_saving(self, scan_saver, events):
        scan_saver._module.saving_payload = lambda: 1 / 0
        scan_saver.get_set_node()

        assert dict(events[0][1].payload) == {}

    def test_a_saving_can_be_ended_when_the_next_one_has_started(self, scan_saver, events):
        scan_saver.get_set_node()
        first = scan_saver.saving
        scan_saver.get_set_node(new=True)  # the next scan of a batch
        second = scan_saver.saving

        scan_saver.end_saving(saving_id=first.saving_id)

        assert [(name, info.saving_id) for name, info in events] == [
            ('started', first.saving_id), ('started', second.saving_id), ('ended', first.saving_id)]
        assert scan_saver.saving.saving_id == second.saving_id  # the second one goes on

    def test_picture_name_depends_on_the_saving(self, scan_saver, events):
        scan_saver.get_set_node()
        first = scan_saver.saving
        scan_saver.get_set_node(new=True)

        assert scan_saver.snapshot_file_path(first.saving_id) != scan_saver.snapshot_file_path()

    def test_unknown_or_ended_saving_is_ignored(self, scan_saver, events):
        scan_saver.get_set_node()
        saving_id = scan_saver.saving.saving_id
        scan_saver.end_saving(saving_id=saving_id)
        scan_saver.end_saving(saving_id=saving_id)
        scan_saver.end_saving(saving_id='unknown')

        assert [name for name, _ in events] == ['started', 'ended']
