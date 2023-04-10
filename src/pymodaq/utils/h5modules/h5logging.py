# -*- coding: utf-8 -*-
"""
Created the 15/11/2022

@author: Sebastien Weber
"""

import logging
import numpy as np

from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.config import Config
from pymodaq.utils.managers.modules_manager import ModulesManager
from pymodaq.utils.h5modules import module_saving, data_saving

from pymodaq.utils.abstract.logger import AbstractLogger
from pymodaq.utils import daq_utils as utils
from .saving import H5Saver
from pymodaq.utils.data import DataToExport


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
        # if name not in self.h5saver.raw_group.children_name():
        #     group = self.h5saver.add_det_group(self.h5saver.raw_group, name, settings)
        #     self.h5saver.add_navigation_axis(np.array([0.0, ]),
        #                                      group, 'time_axis', enlargeable=True,
        #                                      title='Time axis',
        #                                      metadata=dict(label='Time axis', units='s', nav_index=0))

    def add_actuator(self, name, settings):
        pass
        # if name not in self.h5saver.raw_group.children_name():
        #     group = self.h5saver.add_move_group(self.h5saver.raw_group, name, settings)
        #     self.h5saver.add_navigation_axis(np.array([0.0, ]),
        #                              group, 'time_axis', enlargeable=True,
        #                              title='Time axis',
        #                              metadata=dict(label='Time axis', units='s', nav_index=0))

    def add_data(self, data: DataToExport):
        self.module_and_data_saver.add_data()

        # name = data['name']
        # group = self.h5saver.get_group_by_title(self.h5saver.raw_group, name)
        # time_array = self.h5saver.get_node(group, 'Logger_time_axis')
        # time_array.append(np.array([data['acq_time_s']]))
        #
        # data_types = ['data0D', 'data1D']
        # if self.settings['save_2D']:
        #     data_types.extend(['data2D', 'dataND'])
        #
        # for data_type in data_types:
        #     if data_type in data.keys() and len(data[data_type]) != 0:
        #         if not self.h5saver.is_node_in_group(group, data_type):
        #             data_group = self.h5saver.add_data_group(group, data_type, metadata=dict(type='scan'))
        #         else:
        #             data_group = self.h5saver.get_node(group, utils.capitalize(data_type))
        #         for ind_channel, channel in enumerate(data[data_type]):
        #             channel_group = self.h5saver.get_group_by_title(data_group, channel)
        #             if channel_group is None:
        #                 channel_group = self.h5saver.add_CH_group(data_group, title=channel)
        #                 data_array = self.h5saver.add_data(channel_group, data[data_type][channel],
        #                                            scan_type='scan1D', enlargeable=True)
        #             else:
        #                 data_array = self.h5saver.get_node(channel_group, 'Data')
        #             if data_type == 'data0D' and not isinstance(data[data_type][channel]['data'], np.ndarray):
        #                 #this is a security as accessing an element in an array can be converted
        #                 # to a scalar... Made some other attempts but found this is the most reliable here.
        #                 logger.debug('Some data seems to not be properly formated as ndarrays')
        #                 data_array.append(np.array([data[data_type][channel]['data']]))
        #             else:
        #                 data_array.append(data[data_type][channel]['data'])
        # self.h5saver.flush()
        self.settings.child('N_saved').setValue(self.settings.child('N_saved').value() + 1)

    def stop_logger(self):
        self.h5saver.flush()
