from collections import OrderedDict
from qtpy import QtWidgets
from qtpy.QtCore import QObject, Signal, Slot

from pymodaq.utils import data as data_mod
from pymodaq.utils.plotting.utils.filter import Filter
from pymodaq.utils import daq_utils as utils
from pymodaq.utils import gui_utils as gutils
from pymodaq.utils.exceptions import ViewerError
import datetime


DATATYPES = {'Viewer0D': 'Data0D', 'Viewer1D': 'Data1D', 'Viewer2D': 'Data2D', 'ViewerND': 'DataND',
             'ViewerSequential': 'DataSequential'}


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

    data_to_export_signal: Signal[OrderedDict]
    ROI_changed: Signal
    crosshair_dragged: Signal[float, float]
    crosshair_clicked: Signal[bool]
    sig_double_clicked: Signal[float, float]
    status_signal: Signal[str]
    """
    data_to_export_signal = Signal(OrderedDict)  # OrderedDict(name=self.DAQ_type,data0D=None,data1D=None,data2D=None)
    _data_to_show_signal = Signal(data_mod.DataFromPlugins)

    ROI_changed = Signal()
    crosshair_dragged = Signal(float, float)  # Crosshair position in units of scaled top/right axes
    status_signal = Signal(str)
    crosshair_clicked = Signal(bool)
    sig_double_clicked = Signal(float, float)

    def __init__(self, parent=None, title=''):
        super().__init__()
        self.title = title if title != '' else self.__class__.__name__

        self._raw_datas = None
        self.data_to_export = OrderedDict(name=self.title)
        self.view = None

        if parent is None:
            parent = QtWidgets.QWidget()
            parent.show()
        self.parent = parent

        self._display_temporary = False

    @property
    def viewer_type(self):
        """str: the viewer data type see DATA_TYPES"""
        return DATATYPES[self.__class__.__name__]

    def show_data(self, data: data_mod.DataFromPlugins):
        """Entrypoint to display data into the viewer

        Parameters
        ----------
        data: data_mod.DataFromPlugins
        """
        if len(data['data'][0].shape) != 2:
            raise ViewerError(f'Ndarray of dim: {len(data["data"][0].shape)} cannot be plotted'
                              f' using a {self.viewer_type}')
        self.data_to_export = OrderedDict(name=self.title, data0D=OrderedDict(), data1D=OrderedDict())
        self.data_to_export['acq_time_s'] = datetime.datetime.now().timestamp()
        self._raw_datas = data

        self._display_temporary = False

        self._show_data(data)

    def show_data_temp(self, data: data_mod.DataFromPlugins):
        """Entrypoint to display temporary data into the viewer

        No processed data signal is emitted from the viewer

        Parameters
        ----------
        data: data_mod.DataFromPlugins
        """
        self._display_temporary = True
        self.show_data(data)

    def _show_data(self, data: data_mod.DataFromPlugins):
        """Specific viewers should implement it"""
        raise NotImplementedError

    def add_attributes_from_view(self):
        """Convenience function to set attributes to self for the public API
        """
        for attribute in self.convenience_attributes:
            if hasattr(self.view, attribute):
                setattr(self, attribute, getattr(self.view, attribute))

    def activate_roi(self, activate=True):
        """Activate the Roi manager using the corresponding action"""
        raise NotImplementedError