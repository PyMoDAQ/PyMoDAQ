from abc import ABC, abstractmethod


class AbstractLogger(ABC):
    """
    Minimal set of methods a class should implement to be considered as a logger in PyMoDAQ and used by the DAQ_Logger
    extension

    See Also
    --------
    pymodaq.daq_utils.h5modules.H5Logger or pymodaq.daq_utils.db.db_logger.DbLoggerGUI
    """
    @abstractmethod
    def close(self):
        pass

    @property
    @abstractmethod
    def settings_tree(self):
        pass

    @property
    @abstractmethod
    def settings(self):
        pass

    @abstractmethod
    def init_logger(self, settings):
        pass

    @abstractmethod
    def get_handler(self):
        """
        returns a log handler to save the output of the error log into the particular implementation of the Logger object
        """
        pass

    @abstractmethod
    def add_detector(self, det_name, settings):
        pass

    @abstractmethod
    def add_datas(self, datas):
        pass

    @abstractmethod
    def stop_logger(self):
        pass