
from qtpy import QtCore
from qtpy.QtCore import QObject, Signal

from pymodaq.utils.managers.modules import ModulesManager
from pymodaq_data import DataToExport, Axis
from pymodaq_gui.managers.h5manager import H5Manager

from pymodaq_gui.managers.runner_thread_manager import WorkerThreadManager

from pymodaq.utils.h5modules.module_saving import (
    ExtensionSaver, DataBundle, ScanSaver, LoggerSaver, OptimizerSaver)
from pymodaq.utils.custom_ext import CustomExt
from pymodaq_gui.parameter import Parameter
from pymodaq_utils.utils import ThreadCommand


class SaverWorker(QObject):
    """ Worker in separated thread receiving the data ad DataBundle
    and adding them into the extended or enlargeable arrays within a H5file using one of the
    ExtensionSaver module saver """

    n_saved = Signal(int)
    data_to_save_signal = Signal(DataBundle)
    nav_axes_signal = Signal(list)

    def __init__(self, saver: ScanSaver | LoggerSaver | OptimizerSaver):
        super().__init__()
        self.saver: ScanSaver | LoggerSaver | OptimizerSaver = saver
        self._n_saved = 0

        self.data_to_save_signal.connect(self.save_data, QtCore.Qt.ConnectionType.QueuedConnection)
        self.nav_axes_signal.connect(self.add_nav_axes, QtCore.Qt.ConnectionType.QueuedConnection)

    @QtCore.Slot(DataBundle)
    def save_data(self, data: DataBundle):
        self.saver.add_data_bundle(data)

        self._n_saved += 1
        self.n_saved.emit(self._n_saved)

    @QtCore.Slot(list)
    def add_nav_axes(self, axes: list[Axis]):
        """ Particular case of the ScanSaver where the Navigations axes are the
        same for all nodes and can therefore be added beforehand"""
        self.saver.add_nav_axes(axes)


class ExtensionWorker(QObject):
    """
        =========================== ========================================

        =========================== ========================================

    """
    _worker_done = QtCore.Signal()

    #these below should be added as top children in the extension settings
    params = [
        {'title': 'Worker:', 'name': 'worker', 'type': 'group', 'children': [
            {'title': 'Worker Running:', 'name': 'worker_running', 'type': 'led', 'value': False, 'readonly': True},
            {'title': 'Worker tasks:', 'name': 'worker_tasks', 'type': 'int', 'value': 0, 'readonly': True},
        ]},
    ]

    def __init__(self, app: CustomExt, parent=None):

        """
        DAQScanAcquisition deal with the acquisition part of daq_scan, that is transferring commands to modules,
        getting back data, saviong and letting know th UI about the scan status

        """

        super().__init__(parent)
        self._app = app

        self.thread_manager = WorkerThreadManager(parent=self)

        self.saver_worker: SaverWorker = None
        self._n_emitted = 0

        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def h5_manager(self) -> H5Manager:
        """ Convenience property"""
        return self._app.h5_manager

    @property
    def modules_manager(self) -> ModulesManager:
        """ Convenience property"""
        return self._app.modules_manager

    @property
    def settings(self) -> Parameter:
        return self._app.settings

    @property
    def module_and_data_saver(self) -> ScanSaver | LoggerSaver | OptimizerSaver:
        """ Convenience property"""
        return self._app.module_and_data_saver

    def start(self):
        self._running = True
        self._n_emitted = 0
        if self._app.has_action('start'):
            self._app.set_action_enabled('start', False)
        self._init_saver_worker_and_start_it()
        self._start()

    def pause(self, do_pause: bool = True):
        if do_pause:
            self._running = False
        else:
            self._running = True

        if do_pause:
            message = "Extension has been paused"
        else:
            message = "Extension resumed"

        self._update_status(message)
        self.modules_manager.enable_modules(do_pause)
        self._pause(do_pause)

    def stop(self, msg: str = None):
        self._running = False

        try:  # 1 immediately stop the emission of data to the saver worker
            self.saver_worker.data_to_save_signal.disconnect(self.saver_worker.save_data)
        except (TypeError, AttributeError):
            pass

        self._stop(msg)

        self.modules_manager.connect_actuators(False)
        self.modules_manager.connect_detectors(False)
        self.modules_manager.enable_modules(True)

        # 3 terminate the saver worker once its queue is empty
        if self.settings['worker', 'worker_tasks'] == 0:
            self.terminate_worker()
        else:
            self._worker_done.connect(self.terminate_worker)

        # 4 update the GUI
        if self._app.has_action('pause'):
            self._app.set_action_checked('pause', False)
        if self._app.has_action('start'):
            self._app.set_action_enabled('start', True)
        self._update_status(msg)

    def _init_saver_worker_and_start_it(self):
        try:
            self._worker_done.disconnect(self.terminate_worker)
        except TypeError:
            pass

        # managing saver worker
        self.module_and_data_saver.h5saver = self._app.h5saver

        self.saver_worker = SaverWorker(saver=self.module_and_data_saver, )
        self.thread_manager.create_thread_for_worker('saver', self.saver_worker)
        self.saver_worker.n_saved.connect(self.update_worker_ntask)
        self.thread_manager.start_thread('saver')
        self.settings['worker', 'worker_running'] = True

    @QtCore.Slot(int)
    def update_worker_ntask(self, n_saved: int):
        n_tasks = self._n_emitted - n_saved
        self.settings['worker', 'worker_tasks'] = n_tasks

        if n_tasks == 0:
            self._worker_done.emit()

    def terminate_worker(self):
        """ Will terminate/close/stops a few things when the worker is done working"""
        # stopping the plotting before flushing/closing the file
        # 1 disconnecting the connection to here (fired once)
        try:
            self._worker_done.disconnect(self.terminate_worker)
        except TypeError:
            pass
        try:  # 2 disconnect the data production from the saving
            self.saver_worker.data_to_save_signal.disconnect(self.saver_worker.save_data)
        except (AttributeError, TypeError):
            pass

        # 3 quit the thread managing the data saving (nothing left in the loop and no more connection)
        self.thread_manager.exit_worker_thread('saver', delete_worker=True)

        # 4 flushing/closing the file to be able to create new groups...
        self.h5_manager.close_file()
        self.h5_manager.update_file_status_led()

        # 5 updating GUI info
        if hasattr(self._app, 'enable_start_stop'):
            self._app.enable_start_stop(True)
        self.settings['worker', 'worker_running'] = False

    def _update_status(self, msg: str):
        """ convenience method to update the status display
        To be reimplemented"""
        pass


    def _start(self):
        """ To be reimplemented with specifics of your Worker

        Is called automatically after self.start
        """
        raise NotImplementedError

    def _pause(self, do_pause: bool = True):
        """ To be reimplemented with specifics of your Worker

        Is called automatically after self.pause
        """
        raise NotImplementedError

    def _stop(self, msg: str = None):
        """ To be reimplemented with specifics of your Worker

        Is called automatically after self.stop

        You should add in here all signal disconnection and other cleaning things. H5 cleaning
        is handled in the self.stop generic method
        """
        raise NotImplementedError