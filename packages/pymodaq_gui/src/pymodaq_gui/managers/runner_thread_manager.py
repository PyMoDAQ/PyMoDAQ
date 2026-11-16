from dataclasses import dataclass
from typing import Any, Optional

from qtpy import QtCore

from pymodaq_data.h5modules.data_saving import DataBundle
from pymodaq_data import DataToExport


def get_thread_params(worker_setting_name: str) -> list[dict]:
    return [
        {'title': worker_setting_name.replace('_', ' ').title(), 'name': worker_setting_name, 'type': 'group',
         'children': [
            {'title': 'Worker Running:', 'name': 'worker_running', 'type': 'led', 'value': False, 'readonly': True},
            {'title': 'Pending save tasks:', 'name': 'worker_tasks', 'type': 'int', 'value': 0, 'readonly': True,
             'tooltip': 'Scan points queued to be written but not yet saved to disk. Usually near 0 since '
                        'saving is normally faster than acquisition; a sustained non-zero value means the '
                        'saver is falling behind the scan.'},
        ]},
    ]


@dataclass
class DataForProcessor:
    """ To be subclassed if necessary!"""
    node_path: str



class ThreadWorker(QtCore.QObject):

    worker_setting_name: str = 'worker'

    params = get_thread_params(worker_setting_name)

    n_jobs_done_signal = QtCore.Signal(str, int)
    data_to_save_signal = QtCore.Signal(DataBundle)
    data_to_process_signal = QtCore.Signal(DataForProcessor)
    data_processed_signal = QtCore.Signal(DataToExport)
    name = 'ThreadWorker'

    def __init__(self, parent = None):
        """ Base class for any worker to be moved in a thread"""
        super().__init__(parent)
        self._n_jobs_done = 0


class WorkerThreadManager(QtCore.QObject):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.worker_threads: dict[str, QtCore.QThread] = {}
        self.workers: dict[str, Optional[ThreadWorker]] = {}
        self.n_jobs: dict[str, int] = {}

        self.current_name: Optional[str] = None

    @property
    def worker_thread(self) -> Optional[QtCore.QThread]:
        if self.current_name is None:
            return None
        return self.worker_threads.get(self.current_name, None)

    @property
    def worker(self) -> Optional[ThreadWorker]:
        if self.current_name is None:
            return None
        return self.workers.get(self.current_name, None)

    def get_worker(self, name: str) -> Optional[ThreadWorker]:
        return self.workers.get(name, None)

    def get_thread(self, name: str) -> Optional[QtCore.QThread]:
        return self.worker_threads.get(name, None)

    def create_thread_for_worker(self, name: str,
                                 worker: Optional[ThreadWorker],
                                 delete_if_exists: bool = True,
                                 start_thread: bool = False,
                                 thread: Optional[QtCore.QThread] = None
                                 ) -> Optional[QtCore.QThread]:
        """ Create a new thread (or return an existing one) for a worker, and move the worker to it
        I
        t is up to you to connect the worker methods with your main app using Signal/Slot connections

        Do not use direct method call, otherwise the method will be executed in the calling thread
        """
        self.current_name = name
        if delete_if_exists and name in self.worker_threads:
            if  self.worker_threads[name].isRunning():
                self.exit_worker_thread(name)

        if name not in self.worker_threads:
            if thread is None:
                thread = QtCore.QThread()
            self.worker_threads[name] = thread
            self.workers[name] = worker
            if worker is not None:
                worker.moveToThread(thread)

        self.n_jobs[name] = 0

        if start_thread:
            self.worker_threads[name].start()

        return self.worker_threads.get(name)

    def exit_worker_threads(self, delete_worker: bool = False) -> None:
        while len(self.worker_threads) > 0:
            self.exit_worker_thread(self.get_last_name(),
                                    delete_worker=delete_worker)

    def exit_runner_thread(self, duration: int = 5000) -> None:
        """ for back compatibility """
        self.exit_worker_thread(self.current_name, duration)

    @property
    def runner_thread(self) -> Optional[QtCore.QThread]:
        """ for back compatibility """
        last_name = self.get_last_name()
        return None if last_name is None else self.get_thread(last_name)

    @runner_thread.setter
    def runner_thread(self, runner: QtCore.QThread) -> None:
        self.create_thread_for_worker('default', None,
                                      delete_if_exists=False,
                                      start_thread=False,
                                      thread=runner)

    def exit_worker_thread(self,
                           runner_name: Optional[str] = None,
                           duration: int = 5000,
                           delete_worker: bool = False) -> None:
        if runner_name is None:
            runner_name = self.current_name
        runner_thread = self.worker_threads.pop(runner_name, None) if runner_name is not None else None
        worker = self.workers.pop(runner_name, None) if runner_name is not None else None
        if runner_thread is not None:
            runner_thread.quit()
            terminated = runner_thread.wait(duration)
            if not terminated:
                runner_thread.terminate()
                runner_thread.wait()
            runner_thread.deleteLater()
            if delete_worker and worker is not None:
                worker.deleteLater()
        self.current_name = self.get_last_name()

    def get_last_name(self) -> str | None:
        names = list(self.worker_threads.keys())
        if len(names) > 0:
            return names[-1]
        else:
            return None

    def start_thread(self, name: Optional[str] = None) -> None:
        if name is None:
            name = self.current_name
        thread = self.get_thread(name) if name is not None else None
        if thread is not None:
            thread.start()
