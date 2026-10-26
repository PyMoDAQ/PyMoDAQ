"""How the viewer worker calls the grab_data method of a plugin, depending on live_mode_available and
hardware_averaging"""
from types import SimpleNamespace

import numpy as np
import pytest

from pymodaq.control_modules.daq_viewer import DetectorWorker
from pymodaq.control_modules.thread_commands import ControlToHardwareViewer, ThreadStatusViewer

from pymodaq_data.data import DataToExport, DataRaw
from pymodaq_utils.utils import ThreadCommand


class StubPlugin:
    """Counts the calls to grab_data and gives frames to the worker as a real plugin would do"""

    def __init__(self, worker: DetectorWorker, live_mode_available: bool, hardware_averaging: bool,
                 frames_per_call: int = 1, max_calls: int = 20):
        self.worker = worker
        self.live_mode_available = live_mode_available
        self.hardware_averaging = hardware_averaging
        self.frames_per_call = frames_per_call
        self.max_calls = max_calls
        self.calls = 0
        self.stopped = False
        self.controller = None

    def grab_data(self, Naverage=1, live=True, **kwargs):
        self.calls += 1
        if self.calls >= self.max_calls:  # the user would have pressed stop long ago
            self.worker.grab_state = False
        for ind in range(self.frames_per_call):
            self.worker.data_ready(DataToExport('stub', data=[DataRaw('frame', data=[np.full((2, 2), float(ind))])]))

    def stop(self):
        self.stopped = True


def make_worker(live_mode_available, hardware_averaging, **kwargs):
    settings = {('main_settings', 'wait_time'): 0}
    worker = DetectorWorker('camera', settings, SimpleNamespace(module_name='stub', daq_type='DAQ2D'))
    worker.plugin = StubPlugin(worker, live_mode_available, hardware_averaging, **kwargs)
    worker.hardware_averaging = hardware_averaging
    worker.emitted = []
    worker.statuses = []
    worker.data_detector_sig.connect(worker.emitted.append)
    worker.status_sig.connect(lambda status: worker.statuses.append(status.command))
    return worker


def grab(worker, naverage=1):
    worker.queue_command(ThreadCommand(ControlToHardwareViewer.GRAB, dict(Naverage=naverage)))


class TestStreamingPlugin:
    @pytest.mark.parametrize('hardware_averaging', [False, True])
    @pytest.mark.parametrize('naverage', [1, 5])
    def test_grab_data_is_called_once(self, qapp, hardware_averaging, naverage):
        worker = make_worker(True, hardware_averaging, frames_per_call=10)
        grab(worker, naverage)
        assert worker.plugin.calls == 1

    def test_grab_is_not_over_while_the_plugin_streams(self, qapp):
        worker = make_worker(True, False)
        grab(worker)
        assert ThreadStatusViewer.GRAB_STOPPED not in worker.statuses
        worker.queue_command(ThreadCommand(ControlToHardwareViewer.STOP_GRAB))
        assert worker.plugin.stopped
        assert ThreadStatusViewer.GRAB_STOPPED in worker.statuses

    def test_viewer_averages_the_streamed_data(self, qapp):
        worker = make_worker(True, False, frames_per_call=6)
        grab(worker, 3)
        assert len(worker.emitted) == 2

    def test_plugin_averages_the_streamed_data(self, qapp):
        worker = make_worker(True, True, frames_per_call=6)
        grab(worker, 3)
        assert len(worker.emitted) == 6  # each one is already an average


class TestPluginWithoutStreaming:
    @pytest.mark.parametrize('hardware_averaging', [False, True])
    def test_grab_data_is_called_again_for_each_data(self, qapp, hardware_averaging):
        worker = make_worker(False, hardware_averaging, max_calls=10)
        grab(worker)
        assert worker.plugin.calls == 10
        assert ThreadStatusViewer.GRAB_STOPPED in worker.statuses

    def test_single_grab_averaged_by_the_viewer(self, qapp):
        worker = make_worker(False, False)
        worker.queue_command(ThreadCommand(ControlToHardwareViewer.SINGLE, dict(Naverage=4)))
        assert worker.plugin.calls == 4
        assert len(worker.emitted) == 1

    def test_single_grab_averaged_by_the_plugin(self, qapp):
        worker = make_worker(False, True)
        worker.queue_command(ThreadCommand(ControlToHardwareViewer.SINGLE, dict(Naverage=4)))
        assert worker.plugin.calls == 1
        assert len(worker.emitted) == 1


class TestSingleGrabOfAStreamingPlugin:
    @pytest.mark.parametrize('hardware_averaging', [False, True])
    def test_single_grab_ends_by_itself(self, qapp, hardware_averaging):
        worker = make_worker(True, hardware_averaging)
        worker.queue_command(ThreadCommand(ControlToHardwareViewer.SINGLE, dict(Naverage=1)))
        assert worker.plugin.calls == 1
        assert len(worker.emitted) == 1
        assert ThreadStatusViewer.GRAB_STOPPED in worker.statuses
