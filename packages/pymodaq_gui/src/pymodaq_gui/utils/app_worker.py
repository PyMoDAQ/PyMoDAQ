import numpy as np
from dataclasses import dataclass
from qtpy import QtCore
from qtpy.QtCore import QObject, Signal

from pymodaq.utils.managers.modules import ModulesManager
from pymodaq_data import DataToExport, Axis
from pymodaq_data.h5modules.data_saving import DataLoader, DataBundle, DataToExportSaver, DataToExportExtendedSaver, \
    DataToExportEnlargeableSaver, DataToExportTimedSaver
from pymodaq_gui.h5modules.saving import H5Saver
from pymodaq_gui.managers.h5manager import H5Manager

from pymodaq_gui.managers.runner_thread_manager import WorkerThreadManager, ThreadWorker, DataForProcessor, \
    get_thread_params

from pymodaq.utils.h5modules.module_saving import (
    ExtensionSaver, ScanSaver, LoggerSaver, OptimizerSaver)
from pymodaq.utils.custom_ext import CustomExt
from pymodaq_gui.parameter import Parameter
from pymodaq_gui.utils import CustomApp
from pymodaq_gui.utils.custom_app import WorkFlowActions
from pymodaq_utils.utils import ThreadCommand




class SaverWorker(ThreadWorker):
    """ Worker in separated thread receiving the data ad DataBundle
    and adding them into the extended or enlargeable arrays within a H5file using one of the
    ExtensionSaver module saver """

    nav_axes_signal = Signal(list)
    worker_setting_name: str = 'saver_worker'
    name = 'SaverWorker'
    params = get_thread_params(worker_setting_name)

    def __init__(self, saver: ScanSaver | LoggerSaver | OptimizerSaver, parent = None):
        super().__init__(parent)

        self.saver: (ScanSaver | LoggerSaver | OptimizerSaver | DataToExportSaver | DataToExportExtendedSaver |
                     DataToExportEnlargeableSaver | DataToExportTimedSaver) = saver
        self.data_to_save_signal.connect(self.save_data, QtCore.Qt.ConnectionType.QueuedConnection)
        self.nav_axes_signal.connect(self.add_nav_axes, QtCore.Qt.ConnectionType.QueuedConnection)

    @QtCore.Slot(DataBundle)
    def save_data(self, data: DataBundle):
        self.saver.add_data_bundle(data)

        self._n_jobs_done += 1
        self.n_jobs_done_signal.emit(self.name, self._n_jobs_done)

    @QtCore.Slot(list)
    def add_nav_axes(self, axes: list[Axis]):
        """ Particular case of the ScanSaver where the Navigations axes are the
        same for all nodes and can therefore be added beforehand"""
        self.saver.add_nav_axes(axes)


class ProcessorWorker(ThreadWorker):
    worker_setting_name: str = 'processor_worker'
    name = 'ProcessorWorker'

    params = get_thread_params(worker_setting_name)

    def __init__(self, h5saver: H5Saver, parent = None):
        super().__init__(parent)

        self.h5saver = h5saver
        self._data_loader = DataLoader(h5saver, swmr_mode=True)

        self.data_to_process_signal.connect(self.do_process_data, QtCore.Qt.ConnectionType.QueuedConnection)
        self._n_jobs_done = 0

    def do_process_data(self, info: DataForProcessor):
        """ To be reimplemented to process data before reemission using processed_data_signal"""
        pass
        #todo Add the line below eventually adapted!
        dte_out = DataToExport('processed')
        self._n_jobs_done += 1
        self.n_jobs_done_signal.emit(self.name, self._n_jobs_done)
        self.data_processed_signal.emit(dte_out)



class ExtensionWorker(QObject):
    """
        =========================== ========================================

        =========================== ========================================

    """
    _workers_done = QtCore.Signal()
    workers_terminated = QtCore.Signal()

    has_data_processor = False


    #TODO: add params class attribute of the different ThreadWorker you're using as top children in the extension settings


    def __init__(self, app: CustomApp, parent=None):

        """
        DAQScanAcquisition deal with the acquisition part of daq_scan, that is transferring commands to modules,
        getting back data, saviong and letting know th UI about the scan status

        """

        super().__init__(parent)
        self._app = app

        self.thread_manager = WorkerThreadManager(parent=self)

        self.saver_worker: SaverWorker = None
        self._processor_worker: ProcessorWorker = None
        self._processor_worker_class: type[ProcessorWorker] = ProcessorWorker

        self.n_tasks: dict[str, int] = {}

        self._running = False
        self.workers_terminated.connect(self._on_workers_terminated)

    @property
    def processor_worker(self) -> ProcessorWorker:
        return self._processor_worker

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
        for worker_name in self.thread_manager.n_jobs:
            self.thread_manager.n_jobs[worker_name] = 0

        if self._app.has_action('start'):
            self._app.set_action_enabled('start', False)
        self._init_saver_worker_and_start_it()
        if self.has_data_processor:
            self._init_processor_worker_and_start_it()
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
        try:
            self.modules_manager.enable_modules(do_pause)
        except AttributeError:
            pass
        self._pause(do_pause)

    def stop(self, msg: str = None):
        self._running = False

        try:  # 1 immediately stop the emission of data to the saver worker
            if self.saver_worker is not None:
                self.saver_worker.data_to_save_signal.disconnect(self.saver_worker.save_data)
        except (TypeError, AttributeError):
            pass

        try:  # 2 immediately stop the emission of data to the processor worker
            if self.has_data_processor:
                self.processor_worker.data_to_process_signal.disconnect(self._processor_worker.do_process_data)
        except (TypeError, AttributeError):
            pass

        self._stop(msg)

        try:
            self.modules_manager.connect_actuators(False)
            self.modules_manager.connect_detectors(False)
            self.modules_manager.enable_modules(True)
        except AttributeError:
            pass

        # 3 terminate the saver worker once its queue is empty
        if self.settings[SaverWorker.worker_setting_name, 'worker_tasks'] == 0:
            self.terminate_workers()
        else:
            self._workers_done.connect(self.terminate_workers)

        # 4 update the GUI
        self._app.enable_workflow_actions(True,
                                         opposite=WorkFlowActions.PAUSE)
        self._update_status(msg)

    def _init_saver_worker_and_start_it(self):
        try:
            self._workers_done.disconnect(self.terminate_workers)
        except TypeError:
            pass

        # managing saver worker
        self.module_and_data_saver.h5saver = self._app.h5saver
        self.n_tasks[SaverWorker.name] = 0
        self.saver_worker = SaverWorker(saver=self.module_and_data_saver, )
        self.thread_manager.create_thread_for_worker(SaverWorker.name, self.saver_worker)
        self.saver_worker.n_jobs_done_signal.connect(self.update_worker_ntask)
        self.thread_manager.start_thread(SaverWorker.name)
        self.settings[SaverWorker.worker_setting_name, 'worker_running'] = True

    def _init_processor_worker_and_start_it(self):
        try:
            self._workers_done.disconnect(self.terminate_workers)
        except TypeError:
            pass

        # managing processor worker
        self.module_and_data_saver.h5saver = self._app.h5saver
        self.n_tasks[self._processor_worker_class.name] = 0
        self._processor_worker = self._processor_worker_class(h5saver=self.h5_manager.h5saver, )
        self.thread_manager.create_thread_for_worker(self._processor_worker_class.name, self._processor_worker)
        self._processor_worker.n_jobs_done_signal.connect(self.update_worker_ntask)
        self.thread_manager.start_thread(self._processor_worker_class.name)
        self.settings[self._processor_worker_class.worker_setting_name, 'worker_running'] = True

    @QtCore.Slot(str, int)
    def update_worker_ntask(self, worker_name: str, n_saved: int):
        self.n_tasks[worker_name] = self.thread_manager.n_jobs[worker_name] - n_saved
        if worker_name in self.thread_manager.workers:
            self.settings[self.thread_manager.get_worker(worker_name).worker_setting_name, 'worker_tasks'] = (
                self.n_tasks)[worker_name]

        if np.all([n_task == 0 for n_task in self.n_tasks.values()]):
            self._workers_done.emit()

    def terminate_workers(self):
        """ Will terminate/close/stops a few things when the worker is done working"""
        # stopping the plotting before flushing/closing the file
        # 1 disconnecting the connection to here (fired once)
        try:
            self._workers_done.disconnect(self.terminate_workers)
        except TypeError:
            pass
        # 2 disconnecting the connection to the worker update
        if self.has_data_processor:
            self._processor_worker.n_jobs_done_signal.disconnect(self.update_worker_ntask)
        self.saver_worker.n_jobs_done_signal.disconnect(self.update_worker_ntask)

        # 3 quit the threads managing the data saving and data processing
        if self.has_data_processor:
            self.thread_manager.exit_worker_thread(ProcessorWorker.name, delete_worker=True)
        self.thread_manager.exit_worker_thread(SaverWorker.name, delete_worker=True)

        # 4 flushing/closing the file to be able to create new groups...
        self.h5_manager.close_file()
        self.h5_manager.update_file_status_led()

        # 5 updating GUI info
        if hasattr(self._app, 'enable_start_stop'):
            self._app.enable_start_stop(True)
        self.settings[SaverWorker.worker_setting_name, 'worker_running'] = False
        if self.has_data_processor:
            self.settings[self._processor_worker_class.worker_setting_name, 'worker_running'] = False

        self.workers_terminated.emit()

    def _on_workers_terminated(self):
        """ Method to reimplement to finalize things after all workers terminated their jobs in their threads

        """
        pass


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