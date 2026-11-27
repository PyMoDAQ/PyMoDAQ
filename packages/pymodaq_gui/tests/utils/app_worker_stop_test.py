"""ExtensionWorker.stop gives the controls of the modules back before doing anything else"""
from unittest.mock import MagicMock

from qtpy import QtCore

from pymodaq_gui.utils.app_worker import ExtensionWorker


def _worker_with_calls():
    worker = ExtensionWorker.__new__(ExtensionWorker)
    QtCore.QObject.__init__(worker)
    calls = []
    manager = MagicMock()
    manager.enable_modules.side_effect = lambda enable: calls.append(('enable_modules', enable))
    worker._app = MagicMock()
    worker._app.modules_manager = manager
    worker._app.settings.__getitem__.return_value = 0
    worker.saver_worker = None
    worker._stop = lambda msg=None: calls.append(('_stop', msg))
    worker.terminate_workers = lambda: calls.append(('terminate_workers',))
    worker._update_status = lambda msg: calls.append(('status', msg))
    return worker, calls


def test_stop_unlocks_the_modules_first():
    worker, calls = _worker_with_calls()
    worker.stop('stopped')
    assert calls[0] == ('enable_modules', True)
    assert ('_stop', 'stopped') in calls
    assert [c for c in calls if c[0] == 'enable_modules'] == [('enable_modules', True)]
