

from qtpy import QtWidgets
from qtpy.QtCore import QObject, Signal, Slot

from pymodaq.utils.data import DataToExport, DataRaw
from pymodaq.utils.exceptions import ViewerError
from pymodaq.utils.enums import BaseEnum
from pymodaq.utils.factory import ObjectFactory, BuilderBase
from pymodaq.utils.plotting import data_viewers
from pymodaq.utils.managers.parameter_manager import ParameterManager

config_viewers = {
}


class ViewersEnum(BaseEnum):
    Viewer0D = 'Data0D'
    Viewer1D = 'Data1D'
    Viewer2D = 'Data2D'
    ViewerND = 'DataND'
    ViewerSequential = 'DataSequential'


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


class ViewerDispatcher(QObject):

    data_to_export_signal = Signal(DataToExport)
    viewer_changed = Signal(object)

    def __init__(self, parent_widget: QtWidgets.QWidget):
        super().__init__()
        self._parent: QtWidgets.QWidget = parent_widget

        self._parent.setLayout(QtWidgets.QHBoxLayout())
        self._parent.layout().setContentsMargins(0, 0, 0, 0)

        self._viewer: ViewerBase = None
        self._data: DataRaw = None

        self.create_viewer('Viewer2D')

    def __call__(self, *args, **kwargs):
        return self._viewer

    def show(self, show=True):
        self._parent.setVisible(show)

    def create_viewer(self, viewer_type: str):
        self._clearall()
        widget = QtWidgets.QWidget()
        self._parent.layout().addWidget(widget)
        self._viewer: ViewerBase = viewer_factory.get(viewer_type, parent=widget)
        self._viewer.data_to_export_signal.connect(self.data_to_export_signal.emit)
        self.viewer_changed.emit(self._viewer)
        QtWidgets.QApplication.processEvents()
        self._parent.show()

    def _clearall(self):
        children = []
        for i in range(self._parent.layout().count()):
            child = self._parent.layout().itemAt(i).widget()
            if child:
                children.append(child)
                print(child)
        for child in children:
            child.deleteLater()

    def show_data(self, data: DataRaw, **kwargs):
        if self._viewer is None or self._data is None or data.dim != self._data.dim:
            self.create_viewer(ViewersEnum(data.dim.name).name)

        self._data = data
        self._viewer.show_data(data, **kwargs)


class ViewerDispatcherTest(ViewerDispatcher, ParameterManager):

    params = [{'title': 'Show Viewer0D', 'name': 'viewer0D', 'type': 'action', 'visible': True},
              {'title': 'Show Viewer1D', 'name': 'viewer1D', 'type': 'action', 'visible': True},
              {'title': 'Show Viewer2D', 'name': 'viewer2D', 'type': 'action', 'visible': True},
              {'title': 'Show ViewerND', 'name': 'viewerND', 'type': 'action', 'visible': True},
              {'title': 'Show ViewerSequential', 'name': 'viewer_sequential', 'type': 'action', 'visible': True},]

    def __init__(self, parent_widget: QtWidgets.QWidget):
        super().__init__(parent_widget)

        self.settings_tree.show()
        self.connect_things()

    def connect_things(self):
        self.settings.child('viewer0D').sigActivated.connect(lambda: self.create_viewer('Viewer0D'))
        self.settings.child('viewer1D').sigActivated.connect(lambda: self.create_viewer('Viewer1D'))
        self.settings.child('viewer2D').sigActivated.connect(lambda: self.create_viewer('Viewer2D'))
        self.settings.child('viewerND').sigActivated.connect(lambda: self.create_viewer('ViewerND'))
        self.settings.child('viewer_sequential').sigActivated.connect(lambda: self.create_viewer('ViewerSequential'))


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
    _data_to_show_signal = Signal(DataRaw)

    ROI_changed = Signal()
    crosshair_dragged = Signal(float, float)  # Crosshair position in units of scaled top/right axes
    status_signal = Signal(str)
    crosshair_clicked = Signal(bool)
    sig_double_clicked = Signal(float, float)

    def __init__(self, parent=None, title=''):
        super().__init__()
        self.title = title if title != '' else self.__class__.__name__

        self._raw_data = None
        self.data_to_export: DataToExport = DataToExport(name=self.title)
        self.view = None

        if parent is None:
            parent = QtWidgets.QWidget()
            parent.show()
        self.parent = parent

        self._display_temporary = False

    @property
    def viewer_type(self):
        """str: the viewer data type see DATA_TYPES"""
        return ViewersEnum[self.__class__.__name__].value

    def show_data(self, data: DataRaw, **kwargs):
        """Entrypoint to display data into the viewer

        Parameters
        ----------
        data: data_mod.DataFromPlugins
        """
        if len(data.shape) > 4:
            raise ViewerError(f'Ndarray of dim: {len(data.shape)} cannot be plotted'
                              f' using a {self.viewer_type}')
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


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    widget = QtWidgets.QWidget()

    prog = ViewerDispatcherTest(widget)

    sys.exit(app.exec_())
