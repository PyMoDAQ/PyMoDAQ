# -*- coding: utf-8 -*-
"""
Created the 22/01/2023

@author: Sebastien Weber
"""
import os
import sys
from typing import List, Union, Callable

from qtpy import QtWidgets, QtCore

from pymodaq.utils.data import DataToExport, DataFromPlugins, DataDim, enum_checker
from pymodaq.utils.h5modules.data_saving import DataLoader
from pymodaq.utils.h5modules.saving import H5Saver
from pymodaq.utils.plotting.data_viewers.viewer import ViewerBase, ViewersEnum, ViewerDispatcher
from pymodaq.utils.gui_utils import Dock, DockArea


class LoaderPlotter:

    def __init__(self, dockarea):
        self.dockarea = dockarea
        self.dispatcher = ViewerDispatcher(dockarea, title='ViewerDispatcher')
        self._viewers: List[ViewerBase] = []
        self._h5saver: H5Saver = None
        self._data: DataToExport = None
        self.dataloader: DataLoader = None

    @property
    def viewers(self) -> List[ViewerBase]:
        return self.dispatcher.viewers

    def connect_double_clicked(self, slot: Callable):
        for viewer in self.viewers:
            viewer.sig_double_clicked.connect(slot)

    def disconnect(self, slot: Callable):
        for viewer in self.viewers:
            viewer.sig_double_clicked.disconnect(slot)

    def clear_viewers(self):
        self.dispatcher.remove_viewers(0)

    @property
    def h5saver(self):
        return self._h5saver

    @h5saver.setter
    def h5saver(self, h5saver: H5Saver):
        self._h5saver = h5saver
        self.dataloader = DataLoader(h5saver)

    @property
    def data(self) -> DataToExport:
        return self._data

    def load_data(self, filter_dims: List[Union[DataDim, str]] = None, filter_full_names: List[str] = None,
                  remove_navigation: bool = True, group_1D=False):
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

        if group_1D:
            data = self._data.get_data_from_dim('Data1D')
            if len(data) > 0:
                data1D_arrays = []
                labels = []
                for dwa in data:
                    data1D_arrays.extend(dwa.data)
                    labels.extend([f'{dwa.get_full_name()}/{label}' for label in dwa.labels])
                    self._data.remove(dwa)

                data1D = DataFromPlugins('data1D', data=data1D_arrays, labels=labels)
                self._data.append(data1D)

        return self._data

    def load_plot_data(self, **kwargs):
        """Load and plot all data from the current H5Saver

        See Also
        -----
        load_data
        """
        self.load_data(**kwargs)
        self.show_data()

    def show_data(self):
        """Send data to their dedicated viewers
        """
        #self._init_show_data(self._data)
        self.set_data_to_viewers(self._data)

    def _init_show_data(self, data: DataToExport):
        """Processing before showing data
        """
        self._viewer_types = [ViewersEnum(data.dim.name) for data in data]
        self.prepare_viewers(self._viewer_types)

    def prepare_viewers(self, viewers_enum: List[ViewersEnum]):
        self._viewer_types = [enum_checker(ViewersEnum, viewer_enum) for viewer_enum in viewers_enum]
        if self.dispatcher.viewer_types != self._viewer_types:
            self.dispatcher.update_viewers(self._viewer_types)

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
        for ind, _data in enumerate(data.data):
            self.dispatcher.viewers[ind].title = _data.name
            self.dispatcher.viewer_docks[ind].setTitle(_data.name)

            if temp:
                self.dispatcher.viewers[ind].show_data_temp(_data)
            else:
                self.dispatcher.viewers[ind].show_data(_data)


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

    loader = LoaderPlotter(area)
    loader.h5saver = h5saver
    data = loader.load_data(filter_dims=['Data2D', 'Data1D'], group_1D=True)
    loader._init_show_data(data)
    loader.show_data()

    if init_qt:
        sys.exit(app.exec_())
    return loader, win


if __name__ == '__main__':
    main()
