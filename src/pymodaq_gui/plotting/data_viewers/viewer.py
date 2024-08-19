from typing import List, Union
import numpy as np

from qtpy import QtWidgets

from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_data.data import DataToExport, DataWithAxes, Axis, DataSource

from pymodaq_utils.enums import enum_checker
from pymodaq_utils.factory import ObjectFactory
from pymodaq_gui.plotting import data_viewers
from pymodaq_gui.plotting.data_viewers.base import ViewerBase, ViewersEnum
from pymodaq_gui.utils import DockArea, Dock

config_viewers = {}

logger = set_logger(get_module_name(__file__))


def get_viewer_enum_from_axes(Naxes: int):
    if Naxes < 0:
        raise ValueError('Naxes could not be below 0')
    if Naxes == 0:
        viewer_enum = ViewersEnum['Viewer0D']
    elif Naxes == 1:
        viewer_enum = ViewersEnum['Viewer1D']
    elif Naxes == 2:
        viewer_enum = ViewersEnum['Viewer2D']
    else:
        viewer_enum = ViewersEnum['ViewerND']
    return viewer_enum


class ViewerFactory(ObjectFactory):
    def get(self, viewer_name, **kwargs):
        if viewer_name not in ViewersEnum.names():
            raise ValueError(f'{viewer_name} is not a valid PyMoDAQ Viewer: {ViewersEnum.names()}')
        return self.create(viewer_name, **kwargs)

    @property
    def viewers(self):
        return self.keys


@ViewerFactory.register('Viewer0D')
def create_viewer0D(parent: QtWidgets.QWidget = None, **_ignored):
    return data_viewers.viewer0D.Viewer0D(parent)


@ViewerFactory.register('Viewer1D')
def create_viewer1D(parent: QtWidgets.QWidget, **_ignored):
    return data_viewers.viewer1D.Viewer1D(parent)


@ViewerFactory.register('Viewer2D')
def create_viewer2D(parent: QtWidgets.QWidget, **_ignored):
    return data_viewers.viewer2D.Viewer2D(parent)


@ViewerFactory.register('ViewerND')
def create_viewerND(parent: QtWidgets.QWidget, **_ignored):
    return data_viewers.viewerND.ViewerND(parent)


# @ViewerFactory.register('ViewerSequential')
# def create_viewer_sequential(widget: QtWidgets.QWidget, **_ignored):
#     return data_viewers.viewer_sequential.ViewerSequential(widget)


viewer_factory = ViewerFactory()


class ViewerDispatcher:
    """MixIn class to add easy control for adding multuiple data viewers in docks depending on
    data to be plotted

    Parameters
    ----------
    dockarea: DockArea
    title: str
    next_to_dock: Dock
        (deprecated) has no effect
    direction: str
        either 'right', 'left', 'bottom', 'top'.

    """

    def __init__(self, dockarea: DockArea = None, title: str = '', next_to_dock: Dock = None,
                 direction='right'):
        super().__init__()
        self._title = title

        self._next_to_dock = next_to_dock

        if dockarea is None:
            dockarea = DockArea()
            dockarea.show()
        self.dockarea = dockarea

        self._direction = direction

        self._viewer_docks = []
        self._viewer_widgets = []
        self._viewer_types = []
        self._viewers = []

    @property
    def viewers(self) -> List[ViewerBase]:
        return self._viewers

    @property
    def viewer_docks(self) -> List[Dock]:
        return self._viewer_docks

    @property
    def viewer_widgets(self) -> List[QtWidgets.QWidget]:
        return self._viewer_widgets

    @property
    def viewer_types(self) -> List[ViewersEnum]:
        return self._viewer_types

    def remove_viewers(self, Nviewers_to_leave: int = 0):
        """Remove viewers from the list after index Nviewers_to_leave

        Parameters
        ----------
        Nviewers

        Returns
        -------

        """
        while len(self.viewer_docks) > Nviewers_to_leave:
            widget = self.viewer_widgets.pop()
            widget.close()
            dock = self.viewer_docks.pop()
            dock.close()
            self.viewers.pop()
            self.viewer_types.pop()
            QtWidgets.QApplication.processEvents()

    def add_viewer(self, viewer_type: ViewersEnum, dock_viewer=None, dock_name=None):
        viewer_type = enum_checker(ViewersEnum, viewer_type)

        if dock_viewer is None:
            if dock_name is None:
                dock_name = f'{self._title}_Viewer_{len(self.viewer_docks) + 1}'
            dock_viewer = Dock(dock_name, size=(350, 350), closable=False)
        self.viewer_docks.append(dock_viewer)

        self._viewer_widgets.append(QtWidgets.QWidget())
        self.viewers.append(viewer_factory.get(viewer_type.name, parent=self._viewer_widgets[-1]))

        self.viewer_types.append(viewer_type)

        self.viewer_docks[-1].addWidget(self._viewer_widgets[-1])
        # if len(self.viewer_docks) == 1:
        #     if self._next_to_dock is not None:
        #         self.dockarea.addDock(self.viewer_docks[-1], 'right', self._next_to_dock)
        #     else:
        #         self.dockarea.addDock(self.viewer_docks[-1])
        # else:
        #     self.dockarea.addDock(self.viewer_docks[-1], 'right', self.viewer_docks[-2])
        self.dockarea.addDock(self.viewer_docks[-1], self._direction)

    def update_viewers(self, viewers_type: List[Union[str, ViewersEnum]],
                       viewers_name: List[str] = None, force=False):
        """

        Parameters
        ----------
        viewers_type: List[ViewersEnum]
        viewers_name: List[str] or None
        force: bool
            if True remove all viewers before update else check if new viewers type are compatible with old ones

        Returns
        -------

        """

        Nviewers_to_leave = 0
        if not force:
            # check if viewers are compatible with new data dim
            for ind, viewer_type in enumerate(viewers_type):
                if len(self.viewer_types) > ind:
                    if viewer_type == self.viewer_types[ind]:
                        Nviewers_to_leave += 1
                    else:
                        break
                else:
                    break
        self.remove_viewers(Nviewers_to_leave)
        ind_loop = 0
        while len(self.viewers) < len(viewers_type):
            self.add_viewer(viewers_type[Nviewers_to_leave + ind_loop],
                            dock_name=viewers_name[Nviewers_to_leave + ind_loop]
                            if viewers_name is not None else None)
            ind_loop += 1
        QtWidgets.QApplication.processEvents()

    def close(self):
        for dock in self.viewer_docks:
            dock.close()

    def show_data(self, data: DataToExport, **kwargs):
        """ Convenience method. Display each dwa in a dedicated data viewer"""
        viewer_types = [ViewersEnum.get_viewers_enum_from_data(dwa) for dwa in data]
        viewer_names = [dwa.name for dwa in data]
        if self.viewer_types != viewer_types:
            self.update_viewers(viewer_types, viewer_names)
        for viewer, dwa in zip(self.viewers, data):
            if len(dwa.axes) != len(dwa.shape):
                dwa.create_missing_axes()
            viewer.show_data(dwa)


if __name__ == '__main__':

    LABEL = 'A Label'
    UNITS = 'units'
    OFFSET = -20.4
    SCALING = 0.22
    SIZE = 20
    DATA = OFFSET + SCALING * np.linspace(0, SIZE - 1, SIZE)

    DATA0D = np.array([2.7])
    DATA1D = np.arange(0, 10)
    DATA2D = np.arange(0, 5 * 6).reshape((5, 6))
    DATAND = np.arange(0, 5 * 6 * 3).reshape((5, 6, 3))
    Nn0 = 10
    Nn1 = 5


    def init_axis(data=None, index=0):
        if data is None:
            data = DATA
        return Axis(label=LABEL, units=UNITS, data=data, index=index)


    def init_data(data=None, Ndata=1, axes=[], name='myData', source=DataSource['raw'],
                  labels=None) -> DataWithAxes:
        if data is None:
            data = DATA2D
        return DataWithAxes(name, source, data=[data for ind in range(Ndata)],
                            axes=axes, labels=labels)


    def ini_data_to_export():
        dat1 = init_data(data=DATA2D, Ndata=2, name='data2D')
        dat2 = init_data(data=DATA1D, Ndata=3, name='data1D')
        data = DataToExport(name='toexport', data=[dat1, dat2])
        return dat1, dat2, data

    import sys

    app = QtWidgets.QApplication(sys.argv)

    dockarea = DockArea()
    prog = ViewerDispatcher(dockarea=dockarea, title='Dispatcher')
    dockarea.show()

    _, _, dte = ini_data_to_export()

    # N = 2
    # viewers = ['Viewer0D', 'Viewer1D', 'Viewer2D']
    # viewers = [ViewersEnum[random.choice(viewers)] for ind in range(N)]
    # viewers = ['Viewer2D', 'Viewer2D', ]
    # print(viewers)
    # prog.update_viewers(viewers)

    prog.show_data(dte)

    sys.exit(app.exec_())
