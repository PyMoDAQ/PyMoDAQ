# -*- coding: utf-8 -*-
"""
Created the 05/12/2022

@author: Sebastien Weber
"""
from typing import List

import numpy as np

from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils import math_utils as mutils
from pymodaq.utils import config as configmod
from pymodaq.utils import gui_utils as gutils
from .scan_factory import ScannerFactory, ScannerBase, ScanParameterManager
from .utils import TableModelSequential
from pymodaq.utils.parameter import utils as putils
from pymodaq.utils.parameter.pymodaq_ptypes import TableViewCustom

logger = set_logger(get_module_name(__file__))
config = configmod.Config()


@ScannerFactory.register('Sequential', 'Linear')
class SequentialScanner(ScannerBase, ScanParameterManager):
    params = [
        {'title': 'Sequences', 'name': 'seq_table', 'type': 'table_view', 'delegate': gutils.SpinBoxDelegate},
              ]

    def __init__(self, actuators: List[str]):
        ScanParameterManager.__init__(self)
        self._actuators = actuators

        self.table_model: TableModelSequential = None
        self.table_view: TableViewCustom = None
        self.update_model()

        ScannerBase.__init__(self)

    def update_model(self, init_data=None):
        if init_data is None:
            if self.table_model is not None:
                init_data = []
                names = [row[0] for row in self.table_model.get_data_all()]
                for name in self._actuators:
                    if name in names:
                        ind_row = names.index(name)
                        init_data.append(self.table_model.get_data_all()[ind_row])
                    else:
                        init_data.append([name, 0., 1., 0.1])
            else:
                init_data = [[name, 0., 1., 0.1] for name in self._actuators]
        self.table_model = TableModelSequential(init_data, )
        self.table_view = putils.get_widget_from_tree(self.settings_tree, TableViewCustom)[0]
        self.settings.child('seq_table').setValue(self.table_model)

    def get_pos(self):
        starts = np.array([self.table_model.get_data(ind, 1) for ind in range(self.table_model.rowCount(None))])
        stops = np.array([self.table_model.get_data(ind, 2) for ind in range(self.table_model.rowCount(None))])
        steps = np.array([self.table_model.get_data(ind, 3) for ind in range(self.table_model.rowCount(None))])
        return starts, stops, steps

    def evaluate_steps(self) -> int:
        starts, stops, steps = self.get_pos()
        n_steps = 1
        for ind in range(starts.size):
            n_steps *= np.abs((stops[ind] - starts[ind]) / steps[ind]) + 1
        return n_steps

    @staticmethod
    def pos_above_stops(positions, steps, stops):
        state = []
        for pos, step, stop in zip(positions, steps, stops):
            if step >= 0:
                state.append(pos > stop)
            else:
                state.append(pos < stop)
        return state

    def set_scan(self):
        starts, stops, steps = self.get_pos()
        all_positions = [starts[:]]
        positions = starts[:]
        state = self.pos_above_stops(positions, steps, stops)
        while not state[0]:
            if not np.any(np.array(state)):
                positions[-1] += steps[-1]

            else:
                indexes_true = np.where(np.array(state))
                positions[indexes_true[-1][0]] = starts[indexes_true[-1][0]]
                positions[indexes_true[-1][0] - 1] += steps[indexes_true[-1][0] - 1]

            state = self.pos_above_stops(positions, steps, stops)
            if not np.any(np.array(state)):
                all_positions.append(positions[:])

        self.get_info_from_positions(np.array(all_positions))
