from collections import OrderedDict
from qtpy import QtWidgets
from qtpy.QtCore import QObject, Signal, Slot
from pymodaq.daq_utils.plotting.utils.filter import Filter
from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils import gui_utils as gutils
from pymodaq.daq_utils.exceptions import ViewerError
import datetime


DATATYPES = {'Viewer0D': 'Data0D', 'Viewer1D': 'Data1D', 'Viewer2D': 'Data2D', 'ViewerND': 'DataND',
             'ViewerSequential': 'DataSequential'}


class ViewerBase(QObject):
    data_to_export_signal = Signal(OrderedDict)  # OrderedDict(name=self.DAQ_type,data0D=None,data1D=None,data2D=None)
    _data_to_show_signal = Signal(utils.DataFromPlugins)

    ROI_changed = Signal()
    crosshair_dragged = Signal(float, float)  # Crosshair position in units of scaled top/right axes
    status_signal = Signal(str)
    crosshair_clicked = Signal(bool)
    sig_double_clicked = Signal(float, float)

    def __init__(self, parent=None, title=''):
        super().__init__()
        self.viewer_type = DATATYPES[self.__class__.__name__]
        self.title = title if title != '' else self.__class__.__name__

        self._raw_datas = None
        self.data_to_export = OrderedDict(name=self.title)

        if parent is None:
            parent = QtWidgets.QWidget()
            parent.show()
        self.parent = parent

        self._display_temporary = False

    def show_data(self, datas: utils.DataFromPlugins):
        if len(datas['data'][0].shape) != 2:
            raise ViewerError(f'Ndarray of dim: {len(datas["data"][0].shape)} cannot be plotted'
                              f' using a {self.viewer_type}')
        self.data_to_export = OrderedDict(name=self.title, data0D=OrderedDict(), data1D=OrderedDict())
        self.data_to_export['acq_time_s'] = datetime.datetime.now().timestamp()
        self._raw_datas = datas

        self._display_temporary = False

        self._show_data(datas)

    def show_data_temp(self, datas: utils.DataFromPlugins):
        self._display_temporary = True
        self.show_data(datas)

    def _show_data(self, datas: utils.DataFromPlugins):
        raise NotImplementedError

    def add_attributes_from_view(self):
        """Convenience function to set attributes to self for the public API
        """
        for attribute in self.convenience_attributes:
            if hasattr(self.view, attribute):
                setattr(self, attribute, getattr(self.view, attribute))