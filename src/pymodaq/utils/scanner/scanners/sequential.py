# -*- coding: utf-8 -*-
"""
Created the 05/12/2022

@author: Sebastien Weber
"""
from typing import List, Tuple, TYPE_CHECKING

import numpy as np

from qtpy import QtCore, QtWidgets
from pymodaq_data.data import Axis, DataDistribution
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils import math_utils as mutils
from pymodaq_utils import config as configmod
from pymodaq_gui import utils as gutils
from ..scan_factory import ScannerFactory, ScannerBase, ScanParameterManager
from pymodaq_gui.parameter import utils as putils
from pymodaq_gui.parameter.pymodaq_ptypes import TableViewCustom
from pymodaq.utils.scanner.scan_selector import Selector

logger = set_logger(get_module_name(__file__))
config = configmod.Config()


if TYPE_CHECKING:
    from pymodaq.control_modules.daq_move import DAQ_Move


class TableModelSequential(gutils.TableModel):
    """Table Model for the Model/View Qt framework dedicated to the Sequential scan mode"""
    def __init__(self, data, **kwargs):
        header = ['Actuator', 'Start', 'Stop', 'Step']
        if 'header' in kwargs:
            header = kwargs.pop('header')
        editable = [False, True, True, True]
        if 'editable' in kwargs:
            editable = kwargs.pop('editable')
        super().__init__(data, header, editable=editable, **kwargs)

    def __repr__(self):
        return f'{self.__class__.__name__} from module {self.__class__.__module__}'

    def validate_data(self, row, col, value):
        """
        make sure the values and signs of the start, stop and step values are "correct"
        Parameters
        ----------
        row: (int) row within the table that is to be changed
        col: (int) col within the table that is to be changed
        value: (float) new value for the value defined by row and col

        Returns
        -------
        bool: True is the new value is fine (change some other values if needed) otherwise False
        """
        start = self.data(self.index(row, 1), QtCore.Qt.DisplayRole)
        stop = self.data(self.index(row, 2), QtCore.Qt.DisplayRole)
        step = self.data(self.index(row, 3), QtCore.Qt.DisplayRole)
        isstep = False
        if col == 1:  # the start
            start = value
        elif col == 2:  # the stop
            stop = value
        elif col == 3:  # the step
            isstep = True
            step = value

        if np.abs(step) < 1e-12 or start == stop:
            return False
        if np.sign(stop - start) != np.sign(step):
            if isstep:
                self._data[row][2] = -stop
            else:
                self._data[row][3] = -step
        return True


@ScannerFactory.register()
class SequentialScanner(ScannerBase):
    scan_type = 'Sequential'
    scan_subtype = 'Linear'
    save_settings = False  # not easy to save table content in a toml...
    params = [
        {'title': 'Sequences', 'name': 'seq_table', 'type': 'table_view',
         'delegate': gutils.SpinBoxDelegate},
              ]
    distribution = DataDistribution['uniform']
    n_axes = 1

    def __init__(self, actuators: List['DAQ_Move']):

        self.table_model: TableModelSequential = None
        self.table_view: TableViewCustom = None
        super().__init__(actuators)
        self.update_model()

    @property
    def actuators(self):
        return self._actuators

    @actuators.setter
    def actuators(self, actuators):
        self._actuators = actuators
        base_path = self.actuators_name + [self.scan_type, self.scan_subtype]
        self.config_saver_loader.base_path = base_path
        self.update_model()

    def update_model(self, init_data=None):
        if init_data is None:
            if self.table_model is not None:
                init_data = []
                names = [row[0] for row in self.table_model.get_data_all()]
                for act in self._actuators:
                    if act.title in names:
                        ind_row = names.index(act.title)
                        init_data.append(self.table_model.get_data_all()[ind_row])
                    else:
                        init_data.append([act.title, 0., 1., 0.1])
            else:
                init_data = [[act.title, 0., 1., 0.1] for act in self._actuators]
        self.table_model = TableModelSequential(init_data, )
        self.table_view = putils.get_widget_from_tree(self.settings_tree, TableViewCustom)[0]
        self.settings.child('seq_table').setValue(self.table_model)
        self.n_axes = len(self._actuators)
        self.update_table_view()

    def get_pos(self):
        starts = np.array([self.table_model.get_data(ind, 1)
                           for ind in range(self.table_model.rowCount(None))])
        stops = np.array([self.table_model.get_data(ind, 2)
                          for ind in range(self.table_model.rowCount(None))])
        steps = np.array([self.table_model.get_data(ind, 3)
                          for ind in range(self.table_model.rowCount(None))])
        return starts, stops, steps

    def evaluate_steps(self) -> int:
        starts, stops, steps = self.get_pos()
        n_steps = 1
        for ind in range(starts.size):
            n_steps *= np.abs((stops[ind] - starts[ind]) / steps[ind]) + 1
        return int(n_steps)

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
        all_positions = [starts.copy()]
        positions = starts.copy()
        state = self.pos_above_stops(positions, steps, stops)
        if len(state) != 0:
            while not state[0]:
                if not np.any(np.array(state)):
                    positions[-1] += steps[-1]

                else:
                    indexes_true = np.where(np.array(state))
                    positions[indexes_true[-1][0]] = starts[indexes_true[-1][0]]
                    positions[indexes_true[-1][0] - 1] += steps[indexes_true[-1][0] - 1]

                state = self.pos_above_stops(positions, steps, stops)
                if not np.any(np.array(state)):
                    all_positions.append(positions.copy())

        self.get_info_from_positions(np.array(all_positions))

    def get_nav_axes(self) -> List[Axis]:
        return [Axis(label=f'{act.title}', units=act.units, data=self.axes_unique[ind], index=ind)
                for ind, act in enumerate(self.actuators)]

    def get_indexes_from_scan_index(self, scan_index: int) -> Tuple[int]:
        """To be reimplemented. Calculations of indexes within the scan"""
        return tuple(self.axes_indexes[scan_index])

    def get_scan_shape(self) -> Tuple[int]:
        return tuple([len(axis) for axis in self.axes_unique])

    def update_from_scan_selector(self, scan_selector: Selector):
        coordinates = scan_selector.get_coordinates()
        pass