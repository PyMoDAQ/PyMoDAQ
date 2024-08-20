# -*- coding: utf-8 -*-
"""
Created the 15/11/2022

@author: Sebastien Weber
"""

import logging
import numpy as np

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.config import Config
from pymodaq_gui.h5modules.saving import H5Saver
from pymodaq_data.data import DataToExport

from pymodaq.utils.managers.modules_manager import ModulesManager
from pymodaq.utils.h5modules import module_saving
from .abstract import AbstractLogger


config = Config()

logger = set_logger(get_module_name(__file__))


class H5LogHandler(logging.StreamHandler):
    def __init__(self, h5saver):
        super().__init__()
        self.h5saver = h5saver
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.setFormatter(formatter)

    def emit(self, record):
        msg = self.format(record)
        self.h5saver.add_log(msg)


class H5Logger(AbstractLogger):
    def __init__(self, modules_manager, *args, **kwargs):

        self.title = self.__class__.__name__

        self.modules_manager: ModulesManager = modules_manager
        self.h5saver = H5Saver(*args, save_type='logger', **kwargs)

        self.module_and_data_saver = module_saving.LoggerSaver(self)
        for det in self.modules_manager.detectors_all:
            det.module_and_data_saver = module_saving.DetectorEnlargeableSaver(det)
        self.module_and_data_saver.h5saver = self.h5saver  # will update its h5saver and all submodules's h5saver

    def close(self):
        self.h5saver.close_file()

    @property
    def settings_tree(self):
        return self.h5saver.settings_tree

    @property
    def settings(self):
        return self.h5saver.settings

    def init_logger(self, settings):
        self.h5saver.init_file(update_h5=True, metadata=dict(settings=settings))
        self.h5saver.flush()
        self.module_and_data_saver.h5saver = self.h5saver
        logger_node = self.module_and_data_saver.get_set_node(new=True)
        return True

    def get_handler(self):
        return H5LogHandler(self.h5saver)

    def add_detector(self, name, settings):
        pass

    def add_actuator(self, name, settings):
        pass

    def add_data(self, dte: DataToExport):
        self.module_and_data_saver.add_data(dte)

        self.settings.child('N_saved').setValue(self.settings.child('N_saved').value() + 1)

    def stop_logger(self):
        self.h5saver.flush()
