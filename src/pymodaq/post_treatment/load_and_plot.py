# -*- coding: utf-8 -*-
"""
Created the 22/01/2023

@author: Sebastien Weber
"""
import os
import sys
from typing import List, Union, Callable, Iterable

from qtpy import QtWidgets, QtCore

from pymodaq.utils.data import DataToExport, DataFromPlugins, DataDim, enum_checker
from pymodaq.utils.h5modules.data_saving import DataLoader
from pymodaq.utils.h5modules.saving import H5Saver
from pymodaq.utils.plotting.data_viewers.viewer import ViewerBase, ViewersEnum, ViewerDispatcher
from pymodaq.utils.gui_utils import Dock, DockArea


class LoaderPlotter:

    grouped_data1D_fullname = 'Grouped/Data1D'

    def __init__(self, dockarea):
        self.dockarea = dockarea
        self.dispatcher = ViewerDispatcher(dockarea, title='ViewerDispatcher')
        self._viewers: dict[str, ViewerBase] = None
        self._viewer_docks: dict[str, ViewerBase] = None
        self._viewer_types: List[ViewersEnum] = None
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
                  remove_navigation: bool = True, group_1D=False, average_axis=None, average_index: int = 0):
        self._data = DataToExport('All')
        self.dataloader.load_all('/', self._data)

        if average_axis is not None:
            for ind, data in enumerate(self._data):
                current_data = data.inav[average_index, ...]
                if average_index == 0:
                    data_to_append = data.inav[0:average_index + 1, ...]
                else:
                    data_to_append = data.inav[0:average_index+1, ...].mean(axis=average_axis)
                data_to_append.labels = [f'{label}_averaged' for label in data_to_append.labels]
                current_data.append(data_to_append)
                self._data[ind] = current_data

        if remove_navigation:
            for data in self._data:
                data.nav_indexes = ()
                data.transpose()  # because usual ND data should be plotted here as 2D with the nav axes as the minor
                # (horizontal)

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

                data1D = DataFromPlugins(self.grouped_data1D_fullname.split('/')[1],
                                         data=data1D_arrays, labels=labels,
                                         origin=self.grouped_data1D_fullname.split('/')[0],
                                         axes=dwa.axes)
                self._data.append(data1D)

        return self._data

    def load_plot_data(self, **kwargs):
        """Load and plot all data from the current H5Saver

        See Also
        -----
        load_data
        """
        if 'target_at' in kwargs:
            target_at = kwargs.pop('target_at')
        self.load_data(**kwargs)
        self.show_data(target_at=target_at)

    def show_data(self, **kwargs):
        """Send data to their dedicated viewers
        """
        #self._init_show_data(self._data)
        self.set_data_to_viewers(self._data, **kwargs)

    def _init_show_data(self, data: DataToExport):
        """Processing before showing data
        """
        self._viewer_types = [ViewersEnum(data.dim.name) for data in data]
        self.prepare_viewers(self._viewer_types)

    def prepare_viewers(self, viewers_enum: List[ViewersEnum], viewers_name: List[str] = None):
        if self._viewers is not None:
            while len(self._viewers) > 0:
                self._viewers.pop(list(self._viewers.keys())[0])
                self._viewer_docks.pop(list(self._viewer_docks.keys())[0])

        self._viewer_types = [enum_checker(ViewersEnum, viewer_enum) for viewer_enum in viewers_enum]
        if viewers_name is None or len(viewers_enum) != len(viewers_name):
            viewers_name = [f'DataPlot{ind:02d}' for ind in range(len(self._viewer_types))]

        if self.dispatcher.viewer_types != self._viewer_types:
            self.dispatcher.update_viewers(self._viewer_types)

        self._viewers = dict(zip(viewers_name, self.dispatcher.viewers))
        self._viewer_docks = dict(zip(viewers_name, self.dispatcher.viewer_docks))

    def set_data_to_viewers(self, data: DataToExport, temp=False, target_at: Iterable[float] = None):
        """Process data dimensionality and send appropriate data to their data viewers

        Parameters
        ----------
        data: list of DataFromPlugins
        temp: bool
            if True notify the data viewers to display data as temporary (meaning not exporting processed data from roi)
        target_at: Iterable[float]
            if specified show and plot the roi_target of each viewer at the given position
        See Also
        --------
        ViewerBase, Viewer0D, Viewer1D, Viewer2D
        """
        for ind, _data in enumerate(data.data):
            viewer = self._viewers[_data.get_full_name()]
            self._viewer_docks[_data.get_full_name()].setTitle(_data.name)

            # viewer = self.viewers[ind]
            # self.dispatcher.viewer_docks[ind].setTitle(_data.name)

            viewer.title = _data.name
            if temp:
                viewer.show_data_temp(_data)
            else:
                viewer.show_data(_data)
            if target_at is not None:
                viewer.show_roi_target(True)
                if _data.dim == 'Data1D':
                    viewer.move_roi_target(target_at)
                elif _data.dim == 'Data2D' and _data.distribution == 'uniform':
                    _target_at = target_at.copy()

                    size = [_data.get_axis_from_index(1)[0].scaling]
                    if len(_target_at) == 1:  # means concatenation of 1D data
                        axis = _data.get_axis_from_index(0)[0]
                        size.append(axis.scaling * axis.size)
                        _target_at = list(_target_at) + [axis.offset]
                    else:
                        size.append(_data.get_axis_from_index(0)[0].scaling)
                    viewer.move_roi_target(_target_at, size)

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
