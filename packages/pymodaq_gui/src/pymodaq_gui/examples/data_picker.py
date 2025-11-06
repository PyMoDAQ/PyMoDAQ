from qtpy.QtCore import Qt
from qtpy import QtWidgets

from typing import Optional

from pymodaq_data.data import DataRaw, Axis

from pymodaq_gui.utils.widgets.table import SpinBoxDelegate
from pymodaq_gui.parameter.utils import get_widget_from_tree
from pymodaq_gui.plotting.data_viewers.viewer2D import Viewer2D
from pymodaq_gui.utils.custom_app import CustomApp, Dock, DockArea

from pymodaq_gui.parameter.pymodaq_ptypes.tableview import TableViewCustom
from pymodaq.utils.scanner.scanners.tabular import TableModelTabular


class DataPicker(CustomApp):
    params = [
        {'title': 'picker status', 'name': 'picker_status', 'type': 'led', 'value': False},
        {'title': 'Positions', 'name': 'tabular_table', 'type': 'table_view',
         'delegate': SpinBoxDelegate, 'menu': True}, ]

    def __init__(self, area: DockArea):
        super().__init__(area)

        self.viewer: Optional[Viewer2D] = None
        self.table_model: Optional[TableModelTabular] = None
        self.table_view: Optional[TableViewCustom] = None

        self.setup_ui()

    def setup_docks(self):
        self.docks['viewer'] = Dock('Viewer2D')
        self.dockarea.addDock(self.docks['viewer'], 'right')
        widget = QtWidgets.QWidget()
        self.viewer = Viewer2D(widget)
        self.docks['viewer'].addWidget(widget)

        self.docks['list'] = Dock('List of points')
        self.dockarea.addDock(self.docks['list'], 'right', self.docks['viewer'])
        self.docks['list'].addWidget(self.settings_tree)

        self.setup_table()

    def setup_actions(self):
        self.add_action('save_points', 'Save Points', 'move_contour',
                        tip='If checked, double clicking will put points in the table',
                        checkable=True)

    def setup_menu(self):
        action_menu = self._menubar.addMenu('Actions')
        self.affect_to('save_points', action_menu)

    def connect_things(self):
        self.connect_action('save_points',
                            lambda status: self.settings.child('picker_status').setValue(status))
        self.viewer.sig_double_clicked.connect(self.double_click_action)

    def double_click_action(self, posx: float, posy: float):
        if self.is_action_checked('save_points'):
            xs, ys = self.viewer.view.unscale_axis(posx, posy)
            data_at = self.viewer.view.get_data_at('red', (xs, ys))
            if data_at is not None:
                self.table_model.add_data(self.table_view.currentIndex().row() + 1,
                                          [posx, posy, data_at])

    def show_data(self, data: DataRaw):
        self.viewer.show_data(data)

    def setup_table(self):
        init_data = [[0., 0., 0.]]
        self.table_model = TableModelTabular(init_data, ['x', 'y', 'data'])
        self.table_view = get_widget_from_tree(self.settings_tree, TableViewCustom)[0]
        self.settings.child('tabular_table').setValue(self.table_model)

        self.table_view.horizontalHeader().ResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.table_view.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        self.table_view.setItemDelegate(SpinBoxDelegate())

        self.table_view.setDragEnabled(True)
        self.table_view.setDropIndicatorShown(True)
        self.table_view.setAcceptDrops(True)
        self.table_view.viewport().setAcceptDrops(True)
        self.table_view.setDefaultDropAction(Qt.MoveAction)
        self.table_view.setDragDropMode(QtWidgets.QTableView.InternalMove)
        self.table_view.setDragDropOverwriteMode(False)

        self.table_view.add_data_signal[int].connect(self.table_model.add_data)
        self.table_view.remove_row_signal[int].connect(self.table_model.remove_data)
        self.table_view.load_data_signal.connect(self.table_model.load_txt)
        self.table_view.save_data_signal.connect(self.table_model.save_txt)


def main():
    from pymodaq_gui.utils.utils import mkQApp
    import numpy as np

    app = mkQApp('DataPicker')
    area = DockArea()
    win = QtWidgets.QMainWindow()
    win.setCentralWidget(area)
    data_picker = DataPicker(area)

    Nx = 100
    Ny = 200
    x = (np.linspace(0, Nx - 1, Nx) + 100) / 2
    y = (np.linspace(0, Ny - 1, Ny) - 10) * 2
    from pymodaq.utils.math_utils import gauss2D

    data_red = 3 * gauss2D(x, np.mean(x), (np.max(x)-np.min(x)) / 5, y, np.mean(y), (np.max(y)-np.min(y)) / 5, 1)
    data_red += np.random.random(data_red.shape)
    data_to_plot = DataRaw(name='mydata', distribution='uniform', data=[data_red],
                           axes=[Axis('xaxis', units='m', data=x, index=1),
                                 Axis('yaxis', units='mm', data=y, index=0), ])

    data_picker.show_data(data_to_plot)
    win.show()
    app.exec()


if __name__ == '__main__':
    main()
