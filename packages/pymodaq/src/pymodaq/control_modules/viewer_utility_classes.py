from abc import abstractmethod
from typing import Union, Iterable
from qtpy import QtWidgets
from qtpy.QtCore import QObject, Slot, Signal


from pymodaq.utils.parameter import ioxml
from pymodaq.utils.parameter.utils import get_param_path, get_param_from_name, iter_children
from easydict import EasyDict as edict

import numpy as np
from pymodaq.utils.math_utils import gauss1D, gauss2D
from pymodaq_utils.utils import ThreadCommand, getLineInfo

from pymodaq_utils.config import get_set_local_dir, GlobalConfig

from pymodaq_data.data import DataToExport, DataRaw
from pymodaq_utils.warnings import deprecation_msg
from pymodaq_utils.serialize.mysocket import Socket
from pymodaq_utils.serialize.serializer_legacy import DeSerializer, Serializer
from pymodaq_gui.plotting.items.roi import RoiInfo
from pymodaq.control_modules.thread_commands import ThreadStatus, ThreadStatusViewer
from pymodaq.control_modules.utils import create_controller_param, create_remote_connection_params, ControllerStatus
from pymodaq_gui.qt_utils import mkQApp
from pymodaq_gui.parameter import Parameter
from pymodaq_gui.parameter.ioxml import VALID_FOR_CONFIGURATION

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
        {'title': 'Plugin Config:', 'name': 'plugin_config', 'type': 'bool_push', 'label': 'Show Config', },
        {'title': 'Dynamic:', 'name': 'dynamic', 'type': 'list',
         'limits': config('data','data_saving', 'data_type', 'dynamic'),
         'value': config('data', 'data_saving', 'data_type', 'dynamic')[0]},
        {'title': 'Show data and process:', 'name': 'show_data', 'type': 'bool', 'value': True, },
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
    {'title': 'Detector Settings', 'name': 'detector_settings', 'type': 'group', 'children': []}
]


def main(plugin_file=None, init=True, title='Testing'):
    """
    this method start a DAQ_Viewer object with this defined plugin as detector
    Returns
    -------
    """
    import sys
    from qtpy import QtWidgets
    from pymodaq.utils.gui_utils import DockArea
    from pathlib import Path
    from pymodaq.utils.gui_utils.loader_utils import create_load_daq_viewer
    from pymodaq.control_modules.daq_viewer_ui.viewer_selector import SelectedModule
    from pymodaq.control_modules.instruments import DAQTypesEnum

    app = mkQApp("PyMoDAQ Viewer")

    win = QtWidgets.QMainWindow()
    area = DockArea()
    win.setCentralWidget(area)
    win.resize(1000, 500)
    win.setWindowTitle('PyMoDAQ Viewer')
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


class DAQ_Viewer_base(QObject):
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
        QObject.__init__(self)  # to make sure this is the parent class

        self.parent_parameters_path = []  # this is to be added in the send_param_status to take into account when
        # the current class instance parameter list is a child of some other class
        self.settings = Parameter.create(name='Settings', type='group', children=self.params)
        if params_state is not None:
            if isinstance(params_state, dict):
                self.settings.restoreState(params_state)
            elif isinstance(params_state, Parameter):
                self.settings.restoreState(params_state.saveState())

        if '0D' in str(self.__class__):
            self.plugin_type = '0D'
        elif '1D' in str(self.__class__):
            self.plugin_type = '1D'
        else:
            self.plugin_type = '2D'

        self.settings.sigTreeStateChanged.connect(self.send_param_status)

        self.parent = parent
        self.status = edict(info="", controller=None, initialized=False)
        self.scan_parameters = None

        self.x_axis = None
        self.y_axis = None

        self.controller = None

        if parent is not None:
            self._title = parent.title
        else:
            self._title = "mydetector"

        self.ini_attributes()

        try:
            self.data_grabed_signal.connect(self._emit_dte)
            self.data_grabed_signal_temp.connect(self._emit_dte_temp)
        except Exception as exc:
            print(f"Error with old message signal stuff: {exc}")

    @property
    def is_master(self):
        """ Get the controller master/slave status

        new in version 4.3.0
        """
        return self.settings['controller', 'controller_status'] == ControllerStatus.MASTER

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

    def ini_attributes(self):
        """
        To be reimplemented in subclass
        """
        pass

    def ini_detector_init(self, old_controller=None, new_controller=None,
                          slave_controller=None):
        """Manage the Master/Slave controller issue

        First initialize the status dictionary
        Then check whether this stage is controlled by a multiaxe controller (to be defined for each plugin)
            if it is a multiaxes controller then:
            * if it is Master: init the controller here
            * if it is Slave: use an already initialized controller (defined in the preset of the dashboard)

        Parameters
        ----------
        old_controller: object (deprecated)
            The particular object that allow the communication with the hardware, in general a python wrapper around the
            hardware library. In case of Slave this one comes from a previously initialized plugin
        slave_controller: object
            The particular object that allow the communication with the hardware, in general a python wrapper around the
            hardware library. In case of Slave this one comes from a previously initialized plugin
        new_controller: object
            The particular object that allow the communication with the hardware, in general a python wrapper around the
            hardware library. In case of Master it is the new instance of your plugin controller
        """
        if old_controller is None and slave_controller is not None:
            old_controller = slave_controller
        self.status.update(edict(info="", controller=None, initialized=False))
        if self.settings['controller', 'controller_status'] == ControllerStatus.SLAVE:
            if old_controller is None:
                raise Exception('no controller has been defined externally while this axe is a slave one')
            else:
                controller = old_controller
        else:  # Master stage
            controller = new_controller
        self.controller = controller
        return controller

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

    def commit_settings(self, param):
        """
        To be reimplemented in subclass
        """
        pass

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


    def emit_status(self, status: ThreadCommand):
        """
            Emit the status signal from the given status.

            =============== ============ =====================================
            **Parameters**    **Type**     **Description**
            *status*                       the status information to transmit
            =============== ============ =====================================
        """
        if self.parent is not None:
            self.parent.status_sig.emit(status)
        else:
            print(status)

    def update_scanner(self, scan_parameters):
        # todo check this because ScanParameters has been removed
        self.scan_parameters = scan_parameters

    @Slot(edict)
    def update_settings(self, settings_parameter_dict):
        """
            Update the settings tree from settings_parameter_dict.
            Finally do a commit to activate changes.

            ========================== ============= =====================================================
            **Parameters**              **Type**      **Description**
            *settings_parameter_dict*   dictionnnary  a dictionary listing path and associated parameter
            ========================== ============= =====================================================

            See Also
            --------
            send_param_status, commit_settings
        """
        # settings_parameter_dict=edict(path=path,param=param)
        try:
            path = settings_parameter_dict['path']
            param = settings_parameter_dict['param']
            change = settings_parameter_dict['change']
            try:
                self.settings.sigTreeStateChanged.disconnect(self.send_param_status)
            except Exception:
                pass
            if change == 'value':
                self.settings.child(*path[1:]).setValue(param.value())  # blocks signal back to main UI
            elif change == 'childAdded':
                child = Parameter.create(name='tmp')
                child.restoreState(param.saveState())
                self.settings.child(*path[1:]).addChild(child)  # blocks signal back to main UI
                param = child

            elif change == 'parent':
                children = get_param_from_name(self.settings, param.name())

                if children is not None:
                    path = get_param_path(children)
                    self.settings.child(*path[1:-1]).removeChild(children)

            self.settings.sigTreeStateChanged.connect(self.send_param_status)

            self.commit_settings(param)
        except Exception as e:
            self.emit_status(ThreadCommand(ThreadStatus.UPDATE_STATUS, str(e)))


    def send_param_status(self, param, changes):
        """
            Check for changes in the given (parameter,change,information) tuple list.
            In case of value changed, send the 'update_settings' ThreadCommand with concerned path,data and change as attribute.

            =============== ============================================ ============================
            **Parameters**    **Type**                                    **Description**
            *param*           instance of pyqtgraph parameter             The parameter to check
            *changes*         (parameter,change,information) tuple list   The changes list to course
            =============== ============================================ ============================

            See Also
            --------
            daq_utils.ThreadCommand
        """
        for param, change, data in changes:
            path = self.settings.childPath(param)
            if change == 'childAdded':
                # first create a "copy" of the actual parameter and send this "copy", to be restored in the main UI
                self.emit_status(ThreadCommand(ThreadStatus.UPDATE_SETTINGS,
                                               [self.parent_parameters_path + path, [data[0].saveState(), data[1]],
                                                change]))  # send parameters values/limits back to the GUI. Send kind of a copy back the GUI otherwise the child reference will be the same in both th eUI and the plugin so one of them will be removed

            elif change == 'value' or change == 'limits' or change == 'options':
                self.emit_status(ThreadCommand(ThreadStatus.UPDATE_SETTINGS,
                                               [self.parent_parameters_path + path, data,
                                                change]))  # send parameters values/limits back to the GUI
            elif change == 'parent':
                pass

            pass


if __name__ == '__main__':
    test = DAQ_Viewer_base()
