"""The manager annotating the data saved by a real extension worker (the one of the scan)"""
from unittest.mock import Mock

import numpy as np
import pytest
from qtpy import QtCore

from pymodaq_data.data import DataRaw, DataToExport
from pymodaq_gui.parameter import Parameter
from pymodaq_utils.utils import ThreadCommand

from pymodaq.extensions.scan.daq_scan import DAQScan, DAQScanAcquisition
from pymodaq.utils.managers.modules import ModulesManager

from pymodaq_ontology import manager as manager_module
from pymodaq_ontology.manager import OntologyManager

DIODE = 'http://example.org/moke#PhotodiodeSignalA'


class FakeDAQScan(QtCore.QObject):
    """The minimum of the scan extension needed by its worker"""
    status_sig = QtCore.Signal(ThreadCommand)

    def __init__(self):
        super().__init__()
        self.settings = Parameter.create(name='settings', type='group', children=DAQScan.params)
        for name in ('plot_0d', 'plot_1d'):
            self.settings.child('plot_options', name).setValue(dict(all_items=[], selected=[]))
        self.scanner = Mock()
        self.scanner.scanner.do_process_data = False
        self.scanner.get_indexes_from_scan_index.return_value = (0,)
        self.scanner.get_nav_axes.return_value = []
        self.modules_manager = ModulesManager()
        self.module_and_data_saver = None
        self.status_manager = Mock()
        self.has_action = Mock(return_value=False)

    def set_action_checked(self, action, status):
        pass

    def enable_workflow_actions(self, *args, **kwargs):
        pass


@pytest.fixture
def worker(qtbot, monkeypatch):
    monkeypatch.setattr(DAQScanAcquisition, 'terminate_workers', lambda obj: None)
    worker = DAQScanAcquisition(daq_scan=FakeDAQScan())
    worker.init_things()
    worker.saver_worker = Mock()
    worker.thread_manager = Mock()
    worker.thread_manager.n_jobs = {'SaverWorker': 0}
    worker._ind_average = 0
    return worker


@pytest.fixture
def manager(qtbot, tmp_path, monkeypatch, source):
    monkeypatch.setattr(manager_module, 'get_set_config_dir', lambda name, user=False: tmp_path / name)
    (tmp_path / 'ontology').mkdir()
    manager = OntologyManager()
    qtbot.addWidget(manager.mainwindow)
    manager.set_source(source)
    return manager


def grabbed():
    dwa = DataRaw('diodes', data=[np.zeros((1,)), np.ones((1,))], labels=['diode_A', 'diode_B'], origin='Detector')
    return DataToExport('dte', data=[dwa])


def saved_bundle(worker):
    return worker.saver_worker.data_to_save_signal.emit.call_args[0][0]


def test_first_step_of_a_scan_is_annotated(worker, manager):
    manager.assignment.set('Detector/diodes/diode_A', DIODE)
    manager.attach_worker(worker)
    worker._ind_scan = 0

    worker.det_done(grabbed())

    assert saved_bundle(worker).dte.data[0].semantic_iri == [DIODE, '']


def test_later_steps_and_detached_worker_are_left_alone(worker, manager):
    manager.assignment.set('Detector/diodes/diode_A', DIODE)
    manager.attach_worker(worker)
    worker._ind_scan = 1
    worker.det_done(grabbed())
    assert 'semantic_iri' not in saved_bundle(worker).dte.data[0].extra_attributes

    manager.detach_worker(worker)
    worker._ind_scan = 0
    worker.det_done(grabbed())
    assert 'semantic_iri' not in saved_bundle(worker).dte.data[0].extra_attributes
