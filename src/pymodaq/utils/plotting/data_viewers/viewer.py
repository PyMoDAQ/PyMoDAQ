from typing import List, Union, TYPE_CHECKING, Iterable
import numpy as np

from qtpy import QtWidgets
from qtpy.QtCore import QObject, Signal, Slot

from pyqtgraph.graphicsItems import InfiniteLine, ROI

from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.data import DataToExport, DataRaw, DataWithAxes, Axis, DataSource
from pymodaq.utils.exceptions import ViewerError
from pymodaq.utils.enums import BaseEnum, enum_checker
from pymodaq.utils.factory import ObjectFactory, BuilderBase
from pymodaq.utils.plotting import data_viewers
from pymodaq.utils.gui_utils import DockArea, Dock
from pymodaq.utils.managers.parameter_manager import ParameterManager

if TYPE_CHECKING:
    from pymodaq.utils.plotting.data_viewers.viewer0D import Viewer0D
    from pymodaq.utils.plotting.data_viewers.viewer1D import Viewer1D
    from pymodaq.utils.plotting.data_viewers.viewer2D import Viewer2D
    from pymodaq.utils.plotting.data_viewers.viewerND import ViewerND

config_viewers = {
}

logger = set_logger(get_module_name(__file__))


class ViewersEnum(BaseEnum):
    """enum relating a given viewer with data type"""
    Viewer0D = 'Data0D'
    Viewer1D = 'Data1D'
    Viewer2D = 'Data2D'
    ViewerND = 'DataND'
    ViewerSequential = 'DataSequential'

    def get_dim(self):
        return self.value.split('Data')[1].split('D')[0]

    def increase_dim(self, ndim: int):
        dim = self.get_dim()
        if dim != 'N':
            dim_as_int = int(dim) + ndim
            if dim_as_int > 2:
                dim = 'N'
            else:
                dim = str(dim_as_int)
        else:
            dim = 'N'
        return ViewersEnum[f'Viewer{dim}D']


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


class ViewerBase(QObject):
    """Base Class for data viewers implementing all common functionalities

    Parameters
    ----------
    parent: QtWidgets.QWidget
    title: str

    Attributes
    ----------
    view: QObject
        Ui interface of the viewer

    data_to_export_signal: Signal[DataToExport]
    ROI_changed: Signal
    crosshair_dragged: Signal[float, float]
    crosshair_clicked: Signal[bool]
    sig_double_clicked: Signal[float, float]
    status_signal: Signal[str]
    """
    data_to_export_signal = Signal(DataToExport)
    _data_to_show_signal = Signal(DataWithAxes)

    ROI_changed = Signal()
    crosshair_dragged = Signal(float, float)  # Crosshair position in units of scaled top/right axes
    status_signal = Signal(str)
    crosshair_clicked = Signal(bool)
    sig_double_clicked = Signal(float, float)

    def __init__(self, parent: QtWidgets.QWidget = None, title=''):
        super().__init__()
        self.title = title if title != '' else self.__class__.__name__

        self._raw_data = None
        self.data_to_export: DataToExport = DataToExport(name=self.title)
        self.view: Union[Viewer0D, Viewer1D, Viewer2D, ViewerND] = None

        if parent is None:
            parent = QtWidgets.QWidget()
            parent.show()
        self.parent = parent

        self._display_temporary = False

    @property
    def has_action(self):
        """Convenience method"""
        if hasattr(self.view, 'has_action'):
            return self.view.has_action

    @property
    def is_action_checked(self):
        """Convenience method"""
        if hasattr(self.view, 'is_action_checked'):
            return self.view.is_action_checked

    @property
    def is_action_visible(self):
        """Convenience method"""
        if hasattr(self.view, 'is_action_visible'):
            return self.view.is_action_visible

    @property
    def set_action_checked(self):
        """Convenience method"""
        if hasattr(self.view, 'set_action_checked'):
            return self.view.set_action_checked

    @property
    def set_action_visible(self):
        """Convenience method"""
        if hasattr(self.view, 'set_action_visible'):
            return self.view.set_action_visible

    @property
    def get_action(self):
        """Convenience method"""
        if hasattr(self.view, 'get_action'):
            return self.view.get_action

    @property
    def toolbar(self):
        """Convenience property"""
        if hasattr(self.view, 'toolbar'):
            return self.view.toolbar

    @property
    def viewer_type(self):
        """str: the viewer data type see DATA_TYPES"""
        return ViewersEnum[self.__class__.__name__].value

    def show_data(self, data: DataWithAxes, **kwargs):
        """Entrypoint to display data into the viewer

        Parameters
        ----------
        data: data_mod.DataFromPlugins
        """
        if len(data.shape) > 4:
            raise ViewerError(f'Ndarray of dim: {len(data.shape)} cannot be plotted using a {self.viewer_type}')

        self.data_to_export = DataToExport(name=self.title)
        self._raw_data = data

        self._display_temporary = False

        self._show_data(data, **kwargs)

    def show_data_temp(self, data: DataRaw, **kwargs):
        """Entrypoint to display temporary data into the viewer

        No processed data signal is emitted from the viewer

        Parameters
        ----------
        data: data_mod.DataFromPlugins
        """
        self._display_temporary = True
        self.show_data(data, **kwargs)

    def _show_data(self, data: DataRaw):
        """Specific viewers should implement it"""
        raise NotImplementedError

    def add_attributes_from_view(self):
        """Convenience function to add attributes from the view to self"""
        for attribute in self.convenience_attributes:
            if hasattr(self.view, attribute):
                setattr(self, attribute, getattr(self.view, attribute))

    def trigger_action(self, action_name: str):
        """Convenience function to trigger programmatically one of the action of the related view"""
        if self.has_action(action_name):
            self.get_action(action_name).trigger()

    def activate_roi(self, activate=True):
        """Activate the Roi manager using the corresponding action"""
        raise NotImplementedError

    def setVisible(self, show=True):
        """convenience method to show or hide the paretn widget"""
        self.parent.setVisible(show)

    @property
    def roi_target(self) -> Union[InfiniteLine.InfiniteLine, ROI.ROI]:
        """To be implemented if necessary (Viewer1D and above)"""
        return None

    def move_roi_target(self, pos: Iterable[float] = None, **kwargs):
        """move a specific read only ROI at the given position on the viewer"""
        ...

    def show_roi_target(self, show=True):
        """Show/Hide a specific read only ROI"""
        if self.roi_target is not None:
            self.roi_target.setVisible(show)


class ViewerDispatcher:
    """MixIn class to add easy control for adding multuiple data viewers in docks depending on data to be plotted"""

    def __init__(self, dockarea: DockArea = None, title: str = '', next_to_dock: Dock = None):
        super().__init__()
        self._title = title
        self._next_to_dock = next_to_dock
        if dockarea is None:
            dockarea = DockArea()
            dockarea.show()
        self.dockarea = dockarea

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
        self.dockarea.addDock(self.viewer_docks[-1], 'right')

    def update_viewers(self, viewers_type: List[ViewersEnum], viewers_name: List[str] = None, force=False):
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
                            dock_name=viewers_name[Nviewers_to_leave + ind_loop] if viewers_name is not None else None)
            ind_loop += 1
        QtWidgets.QApplication.processEvents()

    def close(self):
        for dock in self.viewer_docks:
            dock.close()

    def show_data(self, data: DataToExport):
        """ Convenience method. Display each dwa in a dedicated data viewer"""
        viewer_types = [ViewersEnum(dwa.dim.name) for dwa in data]
        if self.viewer_types != viewer_types:
            self.update_viewers(viewer_types)
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
    import random
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
