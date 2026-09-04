from typing import Any

from qtpy import QtCore


class WorkerThreadManager(QtCore.QObject):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.worker_threads: dict[str, QtCore.QThread] = {}
        self.workers: dict[str, QtCore.QObject] = {}

        self.current_name: str = None

    @property
    def worker_thread(self) -> QtCore.QThread:
        return self.worker_threads.get(self.current_name, None)

    @property
    def worker(self) -> QtCore.QObject:
        return self.workers.get(self.current_name, None)

    def get_worker(self, name: str) -> QtCore.QObject:
        return self.workers.get(name, None)

    def get_thread(self, name: str) -> QtCore.QThread:
        return self.worker_threads.get(name, None)

    def create_thread_for_worker(self, name: str,
                                 worker: QtCore.QObject,
                                 delete_if_exists=True,
                                 start_thread=False) -> QtCore.QObject:
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
            self.worker_threads[name] = QtCore.QThread()
            self.workers[name] = worker
            self.workers[name].moveToThread(self.worker_threads[name])

        if start_thread:
            self.worker_threads[name].start()

        return self.worker_threads.get(name)

    def exit_worker_threads(self, delete_worker=False):
        while len(self.worker_threads) > 0:
            self.exit_worker_thread(self.get_last_name(),
                                    delete_worker=delete_worker)

    def exit_runner_thread(self, duration: int = 5000):
        """ for back compatibility """
        self.exit_worker_thread(self.current_name, duration)

    def exit_worker_thread(self,
                           runner_name: str = None,
                           duration : int = 5000,
                           delete_worker=False):
        if runner_name is None:
            runner_name = self.current_name
        runner_thread = self.worker_threads.pop(runner_name, None)
        worker = self.workers.pop(runner_name, None)
        if runner_thread is not None:
            runner_thread.quit()
            terminated = runner_thread.wait(duration)
            if not terminated:
                runner_thread.terminate()
                runner_thread.wait()
            runner_thread.deleteLater()
            if delete_worker:
                worker.deleteLater()
        self.current_name = self.get_last_name()

    def get_last_name(self) -> str | None:
        names = list(self.worker_threads.keys())
        if len(names) > 0:
            return names[-1]
        else:
            return None

    def start_thread(self, name: str = None):
        if name is None:
            name = self.current_name
        self.get_thread(name).start()
