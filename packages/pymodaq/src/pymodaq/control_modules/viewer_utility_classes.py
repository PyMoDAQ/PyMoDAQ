from abc import abstractmethod

HW_KIND = 'detector'
HW_SETTINGS_KEY = f'{HW_KIND}_settings'
from typing import Iterable, Union

from pymodaq_data.data import DataToExport
from pymodaq_gui.plotting.items.roi import RoiInfo
from pymodaq_gui.qt_utils import mkQApp
from pymodaq_utils.config import GlobalConfig, get_set_local_dir
from pymodaq_utils.warnings import deprecation_msg
from qtpy.QtCore import Signal

from pymodaq.control_modules.utils import PluginBase, create_controller_param, create_remote_connection_params

config = GlobalConfig()

local_path = get_set_local_dir()
# look for eventual calibration files
calibs = ['None']
if local_path.joinpath('camera_calibrations').is_dir():
    for file in local_path.joinpath('camera_calibrations').iterdir():
        if 'xml' in file.suffix:
            calibs.append(file.stem)



comon_parameters = [create_controller_param()]  #

params = [
    {'title': 'Main Settings:', 'name': 'main_settings', 'expanded': False, 'type': 'group', 'children': [
        {'title': 'DAQ type:', 'name': 'DAQ_type', 'type': 'list', 'limits': ['DAQ0D', 'DAQ1D', 'DAQ2D', 'DAQND'],
         'readonly': True},
        {'title': 'Detector type:', 'name': 'detector_type', 'type': 'str', 'value': '', 'readonly': True},
        {'title': 'Detector Name:', 'name': 'module_name', 'type': 'str', 'value': '', 'readonly': True},
        {'title': 'Plugin Config:', 'name': 'plugin_config', 'type': 'bool_push', 'label': 'Show Config'},
        {'title': 'Dynamic:', 'name': 'dynamic', 'type': 'list',
         'limits': config('data','data_saving', 'data_type', 'dynamic'),
         'value': config('data', 'data_saving', 'data_type', 'dynamic')[0]},
        {'title': 'Show data and process:', 'name': 'show_data', 'type': 'bool', 'value': True},
        {'title': 'Refresh time (ms):', 'name': 'refresh_time', 'type': 'float', 'value': 50., 'min': 0.},
        {'title': 'Naverage', 'name': 'Naverage', 'type': 'int', 'default': 1, 'value': 1, 'min': 1},
        {'title': 'Show averaging:', 'name': 'show_averaging', 'type': 'bool', 'default': False, 'value': False},
        {'title': 'Live averaging:', 'name': 'live_averaging', 'type': 'bool', 'default': False, 'value': False},
        {'title': 'N Live aver.:', 'name': 'N_live_averaging', 'type': 'int', 'default': 0, 'value': 0,
         'visible': False},
        {'title': 'Wait time (ms):', 'name': 'wait_time', 'type': 'int', 'default': 0, 'value': 00, 'min': 0},
    ] + create_remote_connection_params() + [
        {'title': 'Overshoot options:', 'name': 'overshoot', 'type': 'group', 'visible': True, 'expanded': False,
         'children': [
             {'title': 'Overshoot:', 'name': 'stop_overshoot', 'type': 'bool', 'value': False},
             {'title': 'Overshoot value:', 'name': 'overshoot_value', 'type': 'float', 'value': 0}]},
        {'title': 'Axis options:', 'name': 'axes', 'type': 'group', 'visible': False, 'expanded': False, 'children': [
            {'title': 'Use calibration?:', 'name': 'use_calib', 'type': 'list', 'limits': calibs},
            {'title': 'X axis:', 'name': 'xaxis', 'type': 'group', 'children': [
                {'title': 'Label:', 'name': 'xlabel', 'type': 'str', 'value': "x axis"},
                {'title': 'Units:', 'name': 'xunits', 'type': 'str', 'value': "pxls"},
                {'title': 'Offset:', 'name': 'xoffset', 'type': 'float', 'default': 0., 'value': 0.},
                {'title': 'Scaling', 'name': 'xscaling', 'type': 'float', 'default': 1., 'value': 1.},
            ]},
            {'title': 'Y axis:', 'name': 'yaxis', 'type': 'group', 'children': [
                {'title': 'Label:', 'name': 'ylabel', 'type': 'str', 'value': "y axis"},
                {'title': 'Units:', 'name': 'yunits', 'type': 'str', 'value': "pxls"},
                {'title': 'Offset:', 'name': 'yoffset', 'type': 'float', 'default': 0., 'value': 0.},
                {'title': 'Scaling', 'name': 'yscaling', 'type': 'float', 'default': 1., 'value': 1.},
            ]},
        ]},

    ]},
    {'title': 'Detector Settings', 'name': HW_SETTINGS_KEY, 'type': 'group', 'children': []}
]


def main(plugin_file=None, init=True, title='Testing'):
    """
    this method start a DAQ_Viewer object with this defined plugin as detector
    Returns
    -------
    """
    import sys
    from pathlib import Path

    from qtpy import QtWidgets

    from pymodaq.control_modules.daq_viewer_ui.viewer_selector import SelectedModule
    from pymodaq.control_modules.instruments import DAQTypesEnum
    from pymodaq.utils.gui_utils import DockArea
    from pymodaq.utils.gui_utils.loader_utils import create_load_daq_viewer

    app = mkQApp("PyMoDAQ Viewer")

    if plugin_file is None:
        detector = 'Mock'
        det_type = f'DAQ0D'
    else:
        detector = Path(plugin_file).stem[13:]
        det_type = f'DAQ{Path(plugin_file).stem[4:6].upper()}'


    shared_ui, daq_viewer = create_load_daq_viewer()
    daq_viewer.detector = SelectedModule(DAQTypesEnum[det_type], detector)
    shared_ui.show()

    if init:
        daq_viewer.init_hardware_ui(init)

    sys.exit(app.exec())


class DAQ_Viewer_base(PluginBase):
    """
        ===================== ===================================
        **Attributes**          **Type**
        *hardware_averaging*    boolean
        *data_grabed_signal*    instance of Signal
        *params*                list
        *settings*              instance of pyqtgraph Parameter
        *parent*                ???
        *status*                dictionary
        ===================== ===================================

        See Also
        --------
        send_param_status
    """
    hardware_averaging = False
    live_mode_available = False
    data_grabed_signal = Signal(list)  # will be deprecated use dte_signal
    data_grabed_signal_temp = Signal(list)  # will be deprecated use dte_signal_temp
    dte_signal = Signal(DataToExport)
    dte_signal_temp = Signal(DataToExport)

    params = []

    def __init__(self, parent=None, params_state=None):
        super().__init__(parent, params_state)
        self._title = self._title if parent is not None else "mydetector"
        if '0D' in str(self.__class__):
            self.plugin_type = '0D'
        elif '1D' in str(self.__class__):
            self.plugin_type = '1D'
        else:
            self.plugin_type = '2D'
        self.scan_parameters = None
        self.x_axis = None
        self.y_axis = None
        self.ini_attributes()
        try:
            self.data_grabed_signal.connect(self._emit_dte)
            self.data_grabed_signal_temp.connect(self._emit_dte_temp)
        except Exception as exc:
            print(f"Error with old message signal stuff: {exc}")

    def _emit_dte(self, dte: Union[DataToExport, list]):
        if isinstance(dte, list):
            deprecation_msg('Data emitted from the instrument plugins should be a DataToExport instance'
                            'See: http://pymodaq.cnrs.fr/en/latest/developer_folder/'
                            'instrument_plugins.html#emission-of-data')
            dte = DataToExport('temp', dte)
        self.dte_signal.emit(dte)

    def _emit_dte_temp(self, dte: Union[DataToExport, list]):
        if isinstance(dte, list):
            deprecation_msg('Data emitted from the instrument plugins should be a DataToExport instance'
                            'See: http://pymodaq.cnrs.fr/en/latest/developer_folder/'
                            'instrument_plugins.html#emission-of-data')
            dte = DataToExport('temp', dte)
        self.dte_signal_temp.emit(dte)

    def ini_detector_init(self, old_controller=None, new_controller=None,
                          slave_controller=None):
        """Deprecated — use ini_controller_init instead."""
        import warnings
        warnings.warn("'ini_detector_init' is deprecated, use 'ini_controller_init' instead.",
                      DeprecationWarning, stacklevel=2)
        return self.ini_controller_init(old_controller, new_controller, slave_controller)

    @abstractmethod
    def ini_detector(self, controller=None):
        """
        Mandatory
        To be reimplemented in subclass
        """
        raise NotImplementedError

    @abstractmethod
    def close(self):
        """
        Mandatory
        To be reimplemented in subclass
        """
        raise NotImplementedError

    @abstractmethod
    def grab_data(self, Naverage=1, **kwargs):
        """
        Mandatory
        To be reimplemented in subclass
        """
        raise NotImplementedError

    @abstractmethod
    def stop(self):
        """
        Mandatory
        To be reimplemented in subclass
        """
        raise NotImplementedError

    def roi_select(self, roi_info: RoiInfo, ind_viewer: int = 0):
        """ Every time a ROISelect is updated on a 2D Viewer,
        this method receive the corresponding info

        To be subclassed in a plugin to use the info

        Parameters
        ----------
        roi_info: RoiInfo
        ind_viewer: int
            The index of the viewer (if multiple) in which the roi is declared
        """
        pass

    def crosshair(self, crosshair_info: Iterable[float], ind_viewer: int = 0):
        """ Every time a crosshair is updated, this method receive the corresponding info

        To be subclassed in a plugin to use the info

        Parameters
        ----------
        crosshair_info: list of float
        ind_viewer: int
            The index of the viewer (if multiple) in which the crosshair is declared
        """
        pass


    def update_scanner(self, scan_parameters):
        # todo check this because ScanParameters has been removed
        self.scan_parameters = scan_parameters

if __name__ == '__main__':
    test = DAQ_Viewer_base()
