
from typing import Union, TYPE_CHECKING, Iterable

from pymodaq_utils.enums import BaseEnum
from pyqtgraph.graphicsItems import InfiniteLine, ROI
from qtpy import QtWidgets
from qtpy.QtCore import QObject, Signal, QRectF

from pymodaq_data.data import DataToExport, DataWithAxes, DataDim, DataDistribution

from pymodaq_gui.plotting.utils.plot_utils import RoiInfo

if TYPE_CHECKING:
    from pymodaq_gui.plotting.data_viewers.viewer0D import Viewer0D
    from pymodaq_gui.plotting.data_viewers.viewer1D import Viewer1D
    from pymodaq_gui.plotting.data_viewers.viewer2D import Viewer2D
    from pymodaq_gui.plotting.data_viewers.viewerND import ViewerND


class ViewerError(Exception):
    ...


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

    @classmethod
    def from_n_axes(cls, n_axes: int):
        if n_axes == 0:
            return ViewersEnum['Viewer0D']
        elif n_axes == 1:
            return ViewersEnum['Viewer1D']
        elif n_axes == 2:
            return ViewersEnum['Viewer2D']
        elif n_axes > 2:
            return ViewersEnum['ViewerND']

    @staticmethod
    def get_viewers_enum_from_metadata(dim: DataDim,
                                       distribution: DataDistribution,
                                       n_nav_axes: int,
                                       n_sig_indexes: int,
                                       shape_len: int,
                                       size: int) -> 'ViewersEnum':
        if dim.name == 'Data0D':
            viewer = 'Viewer0D'
        elif dim.name == 'Data1D':
            viewer = 'Viewer1D'
        elif dim.name == 'Data2D':
            viewer = 'Viewer2D'
        else:
            if distribution.name == 'uniform':
                if shape_len < 3:
                    if shape_len == 1 and size == 1:
                        viewer = 'Viewer0D'
                    elif shape_len == 1 and size > 1:
                        viewer = 'Viewer1D'
                    elif shape_len == 2:
                        viewer = 'Viewer2D'
                    else:
                        viewer = 'ViewerND'
                else:
                    viewer = 'ViewerND'
            else:
                if n_sig_indexes == 0:
                    if n_nav_axes == 1:
                        viewer = 'Viewer1D'
                    elif n_nav_axes == 2:
                        viewer = 'Viewer2D'
                    else:
                        viewer = 'ViewerND'
                else:
                    viewer = 'ViewerND'
        return ViewersEnum[viewer]

    @staticmethod
    def get_viewers_enum_from_data(dwa: DataWithAxes) -> 'ViewersEnum':
        if dwa.dim.name == 'Data0D':
            viewer = 'Viewer0D'
        elif dwa.dim.name == 'Data1D':
            viewer = 'Viewer1D'
        elif dwa.dim.name == 'Data2D':
            viewer = 'Viewer2D'
        else:
            if dwa.distribution.name == 'uniform':
                if len(dwa.shape) < 3 and dwa.check_axes_linear():
                    dwa.nav_indexes = ()
                    if len(dwa.shape) == 1 and dwa.size == 1:
                        viewer = 'Viewer0D'
                    elif len(dwa.shape) == 1 and dwa.size > 1:
                        viewer = 'Viewer1D'
                    elif len(dwa.shape) == 2:
                        viewer = 'Viewer2D'
                    else:
                        viewer = 'ViewerND'
                elif len(dwa.shape) == 1 and not dwa.check_axes_linear():
                    viewer = 'Viewer1D'
                    dwa.nav_indexes = ()
                else:
                    viewer = 'ViewerND'
            else:
                if len(dwa.sig_indexes) == 0:
                    if len(dwa.get_nav_axes()) == 1:
                        viewer = 'Viewer1D'
                    elif len(dwa.get_nav_axes()) == 2:
                        viewer = 'Viewer2D'
                    else:
                        viewer = 'ViewerND'
                else:
                    viewer = 'ViewerND'
        return ViewersEnum[viewer]


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
    ROI_select_signal = Signal(QRectF)  # deprecated: use roi_select_signal
    roi_select_signal = Signal(RoiInfo)

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

    def show_data_temp(self, data: DataWithAxes, **kwargs):
        """Entrypoint to display temporary data into the viewer

        No processed data signal is emitted from the viewer

        Parameters
        ----------
        data: data_mod.DataFromPlugins
        """
        self._display_temporary = True
        self.show_data(data, **kwargs)

    def _show_data(self, data: DataWithAxes, *args, **kwargs):
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


