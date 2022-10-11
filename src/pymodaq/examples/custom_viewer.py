from pymodaq.daq_utils.gui_utils.widgets.table import SpinBoxDelegate
from  pymodaq.daq_utils.parameter.utils import get_widget_from_tree
from pymodaq.daq_utils.plotting.data_viewers.viewer2D import Viewer2D
from pymodaq.daq_utils import gui_utils as gutils
from pyqtgraph.dockarea import Dock
from pyqtgraph.parametertree import ParameterTree, Parameter
from pymodaq.daq_utils.parameter.pymodaq_ptypes.tableview import TableViewCustom
from pymodaq.daq_utils.scanner import TableModelTabular
from qtpy.QtCore import QObject, Qt, Slot
from qtpy import QtWidgets


class ViewerPointList(QObject):
    def __init__(self, area):
        super().__init__()
        self.area = area
        self.viewer = None

        self.set_viewer()
        self.set_point_list()
        self.viewer.sig_double_clicked.connect(self.double_click_action)

    @Slot(float, float)
    def double_click_action(self, posx, posy):
        xs, ys = self.viewer.scale_axis(posx, posy)
        data_at = self.viewer.get_data_at('red', (posx, posy))
        if data_at is not None:
            self.table_model.add_data(self.table_view.currentIndex().row() + 1, [xs, ys, data_at])

    def setData(self, data):
        self.viewer.setImage(data_red=data)

    def setXaxis(self, xaxis):
        self.viewer.x_axis = xaxis

    def setYaxis(self, yaxis):
        self.viewer.y_axis = yaxis

    def set_viewer(self):
        dock_viewer = Dock('Viewer2D')
        self.area.addDock(dock_viewer, 'right')
        widget = QtWidgets.QWidget()
        self.viewer = Viewer2D(widget)
        dock_viewer.addWidget(widget)

    def set_point_list(self):
        dock_list = Dock('List of points')
        self.area.addDock(dock_list, 'right')
        params = [{'title': 'Positions', 'name': 'tabular_table', 'type': 'table_view',
                   'delegate': SpinBoxDelegate, 'menu': True}, ]
        self.settings_tree = ParameterTree()
        self.settings = Parameter.create(name='settings', title='Settings', type='group', children=params)
        self.settings_tree.setParameters(self.settings, showTop=False)
        dock_list.addWidget(self.settings_tree)

        init_data = [[0., 0., 0.]]
        self.table_model = TableModelTabular(init_data, ['x', 'y', 'data'])
        self.table_view = get_widget_from_tree(self.settings_tree, TableViewCustom)[0]
        self.settings.child(('tabular_table')).setValue(self.table_model)

        self.table_view.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.table_view.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        styledItemDelegate = QtWidgets.QStyledItemDelegate()
        styledItemDelegate.setItemEditorFactory(SpinBoxDelegate())
        self.table_view.setItemDelegate(styledItemDelegate)

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


if __name__ == '__main__':
    from pymodaq.daq_utils.gui_utils import DockArea
    from pymodaq.daq_utils.daq_utils import Axis
    import sys
    import numpy as np

    app = QtWidgets.QApplication(sys.argv)
    area = DockArea()
    win = QtWidgets.QMainWindow()
    win.setCentralWidget(area)
    viewer = ViewerPointList(area)

    Nx = 100
    Ny = 200
    x = (np.linspace(0, Nx - 1, Nx) + 100) / 2
    y = (np.linspace(0, Ny - 1, Ny) - 10) * 2
    from pymodaq.daq_utils.daq_utils import gauss2D

    data_red = 3 * gauss2D(x, np.mean(x), (np.max(x)-np.min(x)) / 5, y, np.mean(y), (np.max(y)-np.min(y)) / 5, 1)
    data_red += np.random.random(data_red.shape)

    viewer.setData(data_red)
    viewer.setXaxis(Axis(data=x, label='This is x axis', units='au'))
    viewer.setYaxis(Axis(data=y, label='This is y axis', units='au'))
    win.show()
    app.processEvents()
    sys.exit(app.exec_())
