from typing import Union
from qtpy import QtWidgets
from qtpy.QtCore import QObject, Slot, Signal

from pymodaq.utils.parameter import ioxml
from pymodaq.utils.parameter.utils import get_param_path, get_param_from_name, iter_children
from pymodaq.utils.parameter import Parameter
from easydict import EasyDict as edict

import numpy as np
from pymodaq.utils.math_utils import gauss1D, gauss2D
from pymodaq.utils.daq_utils import ThreadCommand, getLineInfo
from pymodaq.utils.config import Config, get_set_local_dir
from pymodaq.utils.tcp_ip.tcp_server_client import TCPServer, tcp_parameters
from pymodaq.utils.data import DataToExport, DataRaw
from pymodaq.utils.messenger import deprecation_msg
from pymodaq.utils.tcp_ip.mysocket import Socket
from pymodaq.utils.tcp_ip.serializer import DeSerializer, Serializer

comon_parameters = [{'title': 'Controller Status:', 'name': 'controller_status', 'type': 'list', 'value': 'Master',
                     'limits': ['Master', 'Slave']}, ]

local_path = get_set_local_dir()
# look for eventual calibration files
calibs = ['None']
if local_path.joinpath('camera_calibrations').is_dir():
    for ind_file, file in enumerate(local_path.joinpath('camera_calibrations').iterdir()):
        if 'xml' in file.suffix:
            calibs.append(file.stem)


config = Config()

params = [
    {'title': 'Main Settings:', 'name': 'main_settings', 'expanded': False, 'type': 'group', 'children': [
        {'title': 'DAQ type:', 'name': 'DAQ_type', 'type': 'list', 'limits': ['DAQ0D', 'DAQ1D', 'DAQ2D', 'DAQND'],
         'readonly': True},
        {'title': 'Detector type:', 'name': 'detector_type', 'type': 'str', 'value': '', 'readonly': True},
        {'title': 'Detector Name:', 'name': 'module_name', 'type': 'str', 'value': '', 'readonly': True},
        {'title': 'Plugin Config:', 'name': 'plugin_config', 'type': 'bool_push', 'label': 'Show Config', },
        {'title': 'Controller ID:', 'name': 'controller_ID', 'type': 'int', 'value': 0, 'default': 0, 'readonly': False},
        {'title': 'Show data and process:', 'name': 'show_data', 'type': 'bool', 'value': True, },
        {'title': 'Refresh time (ms):', 'name': 'refresh_time', 'type': 'float', 'value': 50., 'min': 0.},
        {'title': 'Naverage', 'name': 'Naverage', 'type': 'int', 'default': 1, 'value': 1, 'min': 1},
        {'title': 'Show averaging:', 'name': 'show_averaging', 'type': 'bool', 'default': False, 'value': False},
        {'title': 'Live averaging:', 'name': 'live_averaging', 'type': 'bool', 'default': False, 'value': False},
        {'title': 'N Live aver.:', 'name': 'N_live_averaging', 'type': 'int', 'default': 0, 'value': 0,
         'visible': False},
        {'title': 'Wait time (ms):', 'name': 'wait_time', 'type': 'int', 'default': 0, 'value': 00, 'min': 0},
        {'title': 'Continuous saving:', 'name': 'continuous_saving_opt', 'type': 'bool', 'default': False,
         'value': False},
        {'title': 'TCP/IP options:', 'name': 'tcpip', 'type': 'group', 'visible': True, 'expanded': False, 'children': [
            {'title': 'Connect to server:', 'name': 'connect_server', 'type': 'bool_push', 'label': 'Connect',
             'value': False},
            {'title': 'Connected?:', 'name': 'tcp_connected', 'type': 'led', 'value': False},
            {'title': 'IP address:', 'name': 'ip_address', 'type': 'str',
             'value': config('network', 'tcp-server', 'ip')},
            {'title': 'Port:', 'name': 'port', 'type': 'int', 'value': config('network', 'tcp-server', 'port')},
        ]},
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


def main(plugin_file=None, init=True):
    """
    this method start a DAQ_Viewer object with this defined plugin as detector
    Returns
    -------
    """
    import sys
    from qtpy import QtWidgets
    from pymodaq.utils.gui_utils import DockArea
    from pymodaq.control_modules.daq_viewer import DAQ_Viewer
    from pathlib import Path

    app = QtWidgets.QApplication(sys.argv)
    if config('style', 'darkstyle'):
        import qdarkstyle
        app.setStyleSheet(qdarkstyle.load_stylesheet())

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
    prog = DAQ_Viewer(area, title="Testing")
    win.show()
    prog.daq_type = det_type
    prog.detector = detector
    if init:
        prog.init_hardware_ui()

    sys.exit(app.exec_())


class DAQ_Viewer_base(QObject):
    """
        ===================== ===================================
        **Attributes**          **Type**
        *hardware_averaging*    boolean
        *data_grabed_signal*    instance of Signal
        *params*                list
        *settings*              instance of pyqtgraph Parameter
        *parent*                ???
        *status*                dictionnary
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

        self.data_grabed_signal.connect(self._emit_dte)
        self.data_grabed_signal_temp.connect(self._emit_dte_temp)

    def _emit_dte(self, dte: Union[DataToExport, list]):
        if isinstance(dte, list):
            deprecation_msg(f'Data emitted from the instrument plugins should be a DataToExport instance'
                            f'See: http://pymodaq.cnrs.fr/en/latest/developer_folder/'
                            f'instrument_plugins.html#emission-of-data')
            dte = DataToExport('temp', dte)
        self.dte_signal.emit(dte)

    def _emit_dte_temp(self, dte: Union[DataToExport, list]):
        if isinstance(dte, list):
            deprecation_msg(f'Data emitted from the instrument plugins should be a DataToExport instance'
                            f'See: http://pymodaq.cnrs.fr/en/latest/developer_folder/'
                            f'instrument_plugins.html#emission-of-data')
            dte = DataToExport('temp', dte)
        self.dte_signal_temp.emit(dte)

    def ini_attributes(self):
        """
        To be reimplemented in subclass
        """
        pass

    def ini_detector_init(self, old_controller=None, new_controller=None):
        """Manage the Master/Slave controller issue

        First initialize the status dictionnary
        Then check whether this stage is controlled by a multiaxe controller (to be defined for each plugin)
            if it is a multiaxes controller then:
            * if it is Master: init the controller here
            * if it is Slave: use an already initialized controller (defined in the preset of the dashboard)

        Parameters
        ----------
        old_controller: object
            The particular object that allow the communication with the hardware, in general a python wrapper around the
            hardware library. In case of Slave this one comes from a previously initialized plugin
        new_controller: object
            The particular object that allow the communication with the hardware, in general a python wrapper around the
            hardware library. In case of Master it is the new instance of your plugin controller
        """
        self.status.update(edict(info="", controller=None, initialized=False))
        if self.settings['controller_status'] == "Slave":
            if old_controller is None:
                raise Exception('no controller has been defined externally while this axe is a slave one')
            else:
                controller = old_controller
        else:  # Master stage
            controller = new_controller
        self.controller = controller
        return controller

    def ini_detector(self, controller=None):
        """
        Mandatory
        To be reimplemented in subclass
        """
        raise NotImplemented

    def close(self):
        """
        Mandatory
        To be reimplemented in subclass
        """
        raise NotImplemented

    def grab_data(self, Naverage=1, **kwargs):
        """
        Mandatory
        To be reimplemented in subclass
        """
        raise NotImplemented

    def stop(self):
        """
        Mandatory
        To be reimplemented in subclass
        """
        raise NotImplemented

    def commit_settings(self, param):
        """
        To be reimplemented in subclass
        """
        pass

    def get_axis(self):
        """deprecated"""
        raise DeprecationWarning('get_axis is deprecated add the axes within the DataWithAxes, '
                                 'DataFromPlugins')
        if self.plugin_type == '1D' or self.plugin_type == '2D':
            self.emit_x_axis()

        if self.plugin_type == '2D':
            self.emit_y_axis()

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
            QtWidgets.QApplication.processEvents()
        else:
            print(status)

    def update_scanner(self, scan_parameters):
        #todo check this because ScanParameters has been removed
        self.scan_parameters = scan_parameters

    @Slot(edict)
    def update_settings(self, settings_parameter_dict):
        """
            Update the settings tree from settings_parameter_dict.
            Finally do a commit to activate changes.

            ========================== ============= =====================================================
            **Parameters**              **Type**      **Description**
            *settings_parameter_dict*   dictionnnary  a dictionnary listing path and associated parameter
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
            self.emit_status(ThreadCommand("Update_Status", [str(e), 'log']))



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
                self.emit_status(ThreadCommand('update_settings',
                                               [self.parent_parameters_path + path, [data[0].saveState(), data[1]],
                                                change]))  # send parameters values/limits back to the GUI. Send kind of a copy back the GUI otherwise the child reference will be the same in both th eUI and the plugin so one of them will be removed

            elif change == 'value' or change == 'limits' or change == 'options':
                self.emit_status(ThreadCommand('update_settings', [self.parent_parameters_path + path, data,
                                                                   change]))  # send parameters values/limits back to the GUI
            elif change == 'parent':
                pass

            pass



class DAQ_Viewer_TCP_server(DAQ_Viewer_base, TCPServer):
    """
        ================= ==============================
        **Attributes**      **Type**
        *command_server*    instance of Signal
        *x_axis*            1D numpy array
        *y_axis*            1D numpy array
        *data*              double precision float array
        ================= ==============================

        See Also
        --------
        utility_classes.DAQ_TCP_server
    """
    params_GRABBER = []  # parameters of a client grabber
    command_server = Signal(list)

    message_list = ["Quit", "Send Data 0D", "Send Data 1D", "Send Data 2D", "Send Data ND", "Status", "Done",
                    "Server Closed", "Info",
                    "Infos",
                    "Info_xml", 'x_axis', 'y_axis']
    socket_types = ["GRABBER"]
    params = comon_parameters + tcp_parameters

    def __init__(self, parent=None, params_state=None, grabber_type='2D'):
        """

        Parameters
        ----------
        parent
        params_state
        grabber_type: (str) either '0D', '1D' or '2D'
        """
        self.client_type = "GRABBER"
        DAQ_Viewer_base.__init__(self, parent, params_state)  # initialize base class with commom attribute and methods
        TCPServer.__init__(self, self.client_type)

        self.x_axis = None
        self.y_axis = None
        self.data = None
        self.grabber_type = grabber_type
        self.ind_data = 0
        self.data_mock: DataToExport = None

    def command_to_from_client(self, command: str):
        """Process the command"""
        sock = self.find_socket_within_connected_clients(self.client_type)
        if sock is not None:  # if client self.client_type is connected then send it the command

            if command == 'x_axis':
                raise DeprecationWarning(f'The command {command} is deprecated use the data objects')
            elif command == 'y_axis':
                raise DeprecationWarning(f'The command {command} is deprecated use the data objects')

            else:
                self.send_command(sock, command)

        else:  # else simulate mock data
            if command == "Send Data 0D":
                self.set_0D_Mock_data()
            elif command == "Send Data 1D":
                self.set_1D_Mock_data()
            elif command == "Send Data 2D":
                self.set_2D_Mock_data()
            self.process_cmds('Done')

    def send_data(self, sock: Socket, data: DataToExport):
        """
            To match digital and labview, send again a command.

            =============== ============================== ====================
            **Parameters**   **Type**                       **Description**
            *sock*                                          the socket receipt
            *data*           double precision float array   the data to be sent
            =============== ============================== ====================

            See Also
            --------
            send_command, check_send_data
        """
        self.send_command(sock, 'Done')
        sock.check_sended_with_serializer(data)

    def read_data(self, sock: Socket) -> DataToExport:
        """Read data from the socket
        """
        return DeSerializer(sock).dte_deserialization()

    def data_ready(self, data: DataToExport):
        """
            Send the grabed data signal.
        """
        self.dte_signal.emit(data)

    def command_done(self, command_sock):
        try:
            sock = self.find_socket_within_connected_clients(self.client_type)
            if sock is not None:  # if client self.client_type is connected then send it the command
                data: DataToExport = self.read_data(sock)
            else:
                data = self.data_mock

            if command_sock is None:
                self.data_ready(data)
            else:
                self.send_data(command_sock, data)  # to be send to a client

        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status", [str(e), 'log']))

    def commit_settings(self, param):

        if param.name() in iter_children(self.settings.child(('settings_client')), []):
            grabber_socket: Socket = \
                [client['socket'] for client in self.connected_clients if client['type'] == self.client_type][0]
            grabber_socket.check_sended_with_serializer('set_info')

            path = get_param_path(param)[2:]  # get the path of this param as a list starting at parent 'infos'
            grabber_socket.check_sended_with_serializer(path)

            # send value
            data = ioxml.parameter_to_xml_string(param)
            grabber_socket.check_sended_with_serializer(data)

    def ini_detector(self, controller=None):
        """
            | Initialisation procedure of the detector updating the status dictionnary.
            |
            | Init axes from image , here returns only None values (to tricky to di it with the server and not really
             necessary for images anyway)

            See Also
            --------
            utility_classes.DAQ_TCP_server.init_server, get_xaxis, get_yaxis
        """
        self.settings.child('infos').addChildren(self.params_GRABBER)

        self.init_server()
        self.controller = self.serversocket
        # %%%%%%% init axes from image , here returns only None values (to tricky to di it with the server and not really necessary for images anyway)
        self.x_axis = self.get_xaxis()
        self.y_axis = self.get_yaxis()

        initialized = True
        info = "Server ready"
        return info, initialized

    def close(self):
        """
            Should be used to uninitialize hardware.

            See Also
            --------
            utility_classes.DAQ_TCP_server.close_server
        """
        self.listening = False
        self.close_server()

    def get_xaxis(self):
        """
            Obtain the horizontal axis of the image.

            Returns
            -------
            1D numpy array
                Contains a vector of integer corresponding to the horizontal camera pixels.
        """
        pass
        return self.x_axis

    def get_yaxis(self):
        """
            Obtain the vertical axis of the image.

            Returns
            -------
            1D numpy array
                Contains a vector of integer corresponding to the vertical camera pixels.
        """
        pass
        return self.y_axis

    def grab_data(self, Naverage=1, **kwargs):
        """
            Start new acquisition.
            Grabbed indice is used to keep track of the current image in the average.

            ============== ========== ==============================
            **Parameters**   **Type**  **Description**

            *Naverage*        int       Number of images to average
            ============== ========== ==============================

            See Also
            --------
            utility_classes.DAQ_TCP_server.process_cmds
        """
        try:
            self.ind_grabbed = 0  # to keep track of the current image in the average
            self.Naverage = Naverage
            self.process_cmds("Send Data {:s}".format(self.grabber_type))
            # self.command_server.emit(["process_cmds","Send Data 2D"])

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [getLineInfo() + str(e), "log"]))

    def stop(self):
        """
            not implemented.
        """
        pass
        return ""

    def set_0D_Mock_data(self):
        x = np.linspace(0, 99, 100)
        data_tmp = 10 * gauss1D(x, 50, 10, 1) + 1 * np.random.rand((100))
        self.ind_data += 1
        self.data_mock = DataToExport('mocktcp',
                                      data=[DataRaw('mock',
                                                    data=[np.atleast_1d(np.roll(data_tmp, self.ind_data)[0])])])

    def set_1D_Mock_data(self):
        x = np.linspace(0, 99, 100)
        data_tmp = 10 * gauss1D(x, 50, 10, 1) + 1 * np.random.rand((100))
        self.ind_data += 1
        self.data_mock = DataToExport('mocktcp', data=[DataRaw('mock', data=[np.roll(data_tmp, self.ind_data)])])

    def set_2D_Mock_data(self):
        self.x_axis = np.linspace(0, 50, 50, endpoint=False)
        self.y_axis = np.linspace(0, 30, 30, endpoint=False)
        data_tmp = 10 * gauss2D(self.x_axis, 20, 10,
                                      self.y_axis, 15, 7, 1) + 2 * np.random.rand(len(self.y_axis), len(self.x_axis))
        self.data_mock = DataToExport('mocktcp', data=[DataRaw('mock', data=[data_tmp])])

if __name__ == '__main__':
    prog = DAQ_Viewer_TCP_server()
