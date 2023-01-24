# -*- coding: utf-8 -*-
"""
Created the 22/01/2023

@author: Sebastien Weber
"""
import os
import sys
from typing import List, Union

from qtpy import QtWidgets, QtCore

from pymodaq.utils.data import DataToExport, DataFromPlugins, DataDim, enum_checker
from pymodaq.utils.h5modules.data_saving import DataLoader
from pymodaq.utils.h5modules.saving import H5Saver
from pymodaq.utils.plotting.data_viewers.viewer import ViewerBase, ViewersEnum, ViewerDispatcher
from pymodaq.utils.gui_utils import Dock, DockArea


class LoaderPlotter:

    def __init__(self, dockarea, h5saver: H5Saver):
        self.dockarea = dockarea
        self.ui = ViewerDispatcher(dockarea, title='mydispatchertest')
        self._viewers: List[ViewerBase] = []
        self.h5saver = h5saver
        self._data: DataToExport = None
        self.dataloader = DataLoader(h5saver)

    @property
    def data(self) -> DataToExport:
        return self._data

    def load_data(self, filter_dims: List[Union[DataDim, str]] = None, filter_full_names: List[str] = None,
                  remove_navigation: bool = True):
        self._data = DataToExport('All')
        self.dataloader.load_all('/', self._data)

        if remove_navigation:
            for data in self._data:
                if len(data.shape) == 1 and data.size == 1:
                    data.set_dim(DataDim['Data0D'])
                elif len(data.shape) == 1 and data.size > 1:
                    data.set_dim(DataDim['Data1D'])
                elif len(data.shape) == 2:
                    data.set_dim(DataDim['Data2D'])
                    data.transpose()
                else:
                    data.set_dim(DataDim['DataND'])

        if filter_dims is not None:
            filter_dims[:] = [enum_checker(DataDim, dim) for dim in filter_dims]
            self._data.data[:] = [data for data in self._data if data.dim in filter_dims]

        if filter_full_names is not None:
            self._data.data[:] = [data for data in self._data if data.get_full_name() in filter_full_names]



        return self._data

    def load_plot_data(self):
        self.load_data()
        self.show_data(self._data)

    def show_data(self):
        """Send data to their dedicated viewers
        """
        self._init_show_data(self._data)
        #self.set_data_to_viewers(self._data)

    def _init_show_data(self, data: DataToExport):
        """Processing before showing data
        """
        self._viewer_types = [ViewersEnum(data.dim.name) for data in data]
        if self.ui.viewer_types != self._viewer_types:
            self.ui.update_viewers(self._viewer_types)

    def set_data_to_viewers(self, data: DataToExport, temp=False):
        """Process data dimensionality and send appropriate data to their data viewers

        Parameters
        ----------
        data: list of DataFromPlugins
        temp: bool
            if True notify the data viewers to display data as temporary (meaning not exporting processed data from roi)

        See Also
        --------
        ViewerBase, Viewer0D, Viewer1D, Viewer2D
        """
        for ind, data in enumerate(data.data):
            self.ui.viewers[ind].title = data.name
            self.ui.viewer_docks[ind].setTitle(data.name)

            if temp:
                self.ui.viewers[ind].show_data_temp(data)
            else:
                self.ui.viewers[ind].show_data(data)


def main(init_qt=True):
    if init_qt:  # used for the test suite
        app = QtWidgets.QApplication(sys.argv)

    path = r'C:\Users\weber\Downloads\temp_data.h5'

    h5saver = H5Saver()
    h5saver.open_file(path)

    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Viewer')
    win.show()

    loader = LoaderPlotter(area, h5saver)
    loader.load_data(filter_dims=['Data2D', 'Data1D'])
    loader.show_data()

    if init_qt:
        sys.exit(app.exec_())
    return loader, win


if __name__ == '__main__':
    main()
