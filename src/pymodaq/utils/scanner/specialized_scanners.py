# -*- coding: utf-8 -*-
"""
Created the 05/12/2022

@author: Sebastien Weber
"""
from typing import List

import numpy as np
from qtpy import QtCore, QtWidgets

from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils import math_utils as mutils
from pymodaq.utils import config as configmod
from pymodaq.utils import gui_utils as gutils
from .scan_factory import ScannerFactory, ScannerBase, ScanParameterManager
from .utils import TableModelSequential, TableModelTabular
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

        self.update_table_view()

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

    def update_table_view(self):
        self.table_view.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.table_view.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        styledItemDelegate = QtWidgets.QStyledItemDelegate()
        styledItemDelegate.setItemEditorFactory(gutils.SpinBoxDelegate())
        self.table_view.setItemDelegate(styledItemDelegate)

        self.table_view.setDragEnabled(True)
        self.table_view.setDropIndicatorShown(True)
        self.table_view.setAcceptDrops(True)
        self.table_view.viewport().setAcceptDrops(True)
        self.table_view.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.table_view.setDragDropMode(QtWidgets.QTableView.InternalMove)
        self.table_view.setDragDropOverwriteMode(False)

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


@ScannerFactory.register('Tabular', 'Linear')
class TabularScanner(SequentialScanner):
    params = [
        {'title': 'Positions', 'name': 'tabular_table', 'type': 'table_view', 'delegate': gutils.SpinBoxDelegate,
         'menu': True},
              ]

    def __init__(self, actuators: List[str]):
        super().__init__(actuators)

    def update_model(self, init_data=None):
        if init_data is None:
            init_data = [[0. for name in self._actuators]]

        self.table_model = TableModelTabular(init_data, [name for name in self._actuators])
        self.table_view = putils.get_widget_from_tree(self.settings_tree, TableViewCustom)[0]
        self.settings.child('tabular_table').setValue(self.table_model)

        self.update_table_view()

    def update_table_view(self):
        super().update_table_view()
        self.table_view.add_data_signal[int].connect(self.table_model.add_data)
        self.table_view.remove_row_signal[int].connect(self.table_model.remove_data)
        self.table_view.load_data_signal.connect(self.table_model.load_txt)
        self.table_view.save_data_signal.connect(self.table_model.save_txt)

    def evaluate_steps(self):
        return len(self.table_model)

    def set_scan(self):
        positions = np.array(self.table_model.get_data_all())
        self.get_info_from_positions(self.positions)

    def update_tabular_positions(self, positions: np.ndarray = None):
        """Convenience function to write positions directly into the tabular table

        Parameters
        ----------
        positions: ndarray
            a 2D ndarray with as many columns as selected actuators
        """
        try:
            if positions is None:
                if self.settings.child('tabular_settings',
                                       'tabular_selection').value() == 'Polylines':  # from ROI
                    viewer = self.scan_selector.scan_selector_source

                    if self.settings.child('tabular_settings', 'tabular_subtype').value() == 'Linear':
                        positions = self.scan_selector.scan_selector.getArrayIndexes(
                            spacing=self.settings.child('tabular_settings', 'tabular_step').value())
                    elif self.settings.child('tabular_settings',
                                             'tabular_subtype').value() == 'Adaptive':
                        positions = self.scan_selector.scan_selector.get_vertex()

                    steps_x, steps_y = zip(*positions)
                    steps_x, steps_y = viewer.scale_axis(np.array(steps_x), np.array(steps_y))
                    positions = np.transpose(np.array([steps_x, steps_y]))
                    self.update_model(init_data=positions)
                else:
                    self.update_model()
            elif isinstance(positions, np.ndarray):
                self.update_model(init_data=positions)
            else:
                pass
        except Exception as e:
            logger.exception(str(e))
