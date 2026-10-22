"""PyMoDAQ refuses to initialize a plugin that does not support the system"""
import pytest

from pymodaq.control_modules import daq_move, daq_viewer
from pymodaq.control_modules.daq_move import ActuatorWorker
from pymodaq.control_modules.daq_viewer import DetectorWorker
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base

RESTRICTIONS = [{'supported_platforms': ('notanos',)}, {'supported_architectures': ('notanarchitecture',)}]


def test_base_classes_work_everywhere():
    for base in (DAQ_Move_base, DAQ_Viewer_base):
        assert base.supported_platforms is None and base.supported_architectures is None


@pytest.mark.parametrize('restriction', RESTRICTIONS)
def test_actuator_refused_on_another_system(monkeypatch, restriction):
    refused = type('DAQ_Move_Refused', (DAQ_Move_base,), restriction)
    monkeypatch.setattr(daq_move, 'find_actuator_class_from_name', lambda name: refused)
    worker = ActuatorWorker.__new__(ActuatorWorker)  # the Qt machinery is not needed to call ini_hardware
    worker.plugin = None
    worker.logger = daq_move.logger
    monkeypatch.setattr(ActuatorWorker, 'plugin_name', 'Refused', raising=False)
    status = worker.ini_hardware()
    assert status.initialized is False and 'only works on' in status.info
    assert worker.plugin is None


@pytest.mark.parametrize('restriction', RESTRICTIONS)
def test_detector_refused_on_another_system(monkeypatch, restriction):
    refused = type('DAQ_1DViewer_Refused', (DAQ_Viewer_base,), restriction)
    monkeypatch.setattr(daq_viewer, 'get_viewer_plugins', lambda daq_type, name: ([], refused))
    worker = DetectorWorker.__new__(DetectorWorker)
    worker.logger = daq_viewer.logger
    worker.plugin = None
    monkeypatch.setattr(DetectorWorker, 'plugin_name', 'Refused', raising=False)
    monkeypatch.setattr(DetectorWorker, 'daq_type', type('T', (), {'name': 'DAQ1D'})(), raising=False)
    status = worker.ini_hardware()
    assert status.initialized is False and 'only works on' in status.info
    assert worker.plugin is None
