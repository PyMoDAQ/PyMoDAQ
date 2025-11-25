# -*- coding: utf-8 -*-
"""
Created on Fri Aug 30 12:21:56 2019

@author: Weber
"""
from collections import OrderedDict
import select
from typing import List
import socket
from threading import Timer

import numpy as np
from qtpy.QtCore import QObject, Signal, Slot, QThread
from qtpy import QtWidgets


from pymodaq_utils.utils import getLineInfo, ThreadCommand
from pymodaq_utils import math_utils as mutils
from pymodaq_utils.config import Config
from pymodaq_gui.parameter import utils as putils
from pymodaq_gui.parameter import ioxml
from pymodaq_gui.parameter import Parameter
from pymodaq_data.data import DataToExport

from pymodaq.utils.data import DataFromPlugins, DataActuator
from pymodaq_utils.serialize.mysocket import Socket
from pymodaq_utils.serialize.serializer_legacy import Serializer, DeSerializer
from pymodaq_gui.managers.parameter_manager import ParameterManager

config = Config()

tcp_parameters = [
    {'title': 'Port:', 'name': 'port_id', 'type': 'int', 'value': config('network', 'tcp-server', 'port'), },
    {'title': 'IP:', 'name': 'socket_ip', 'type': 'str', 'value': config('network', 'tcp-server', 'ip'), },
    {'title': 'Settings PyMoDAQ Client:', 'name': 'settings_client', 'type': 'group', 'children': []},
    {'title': 'Infos Client:', 'name': 'infos', 'type': 'group', 'children': []},
    {'title': 'Connected clients:', 'name': 'conn_clients', 'type': 'table',
     'value': dict(), 'header': ['Type', 'adress']}, ]


class TCPClientTemplate:
    def __init__(self, ipaddress="192.168.1.62", port=6341, client_type=""):
        """Create a socket client

        Parameters
        ----------
        ipaddress: (str) the IP address of the server
        port: (int) the port where to communicate with the server
        client_type: (str) should be one of the accepted client_type by the TCPServer instance (within pymodaq it is
                            either 'GRABBER' or 'ACTUATOR'
        """
        #super().__init__()

        self.ipaddress = ipaddress
        self.port = port
        self._socket: Socket = None
        self._deserializer: DeSerializer = None
        self.connected = False
        self.client_type = client_type
        self.timer = Timer(0.1, self.poll_connection)

    @property
    def socket(self) -> Socket:
        return self._socket

    @socket.setter
    def socket(self, sock: Socket):
        self._socket = sock
        self._deserializer = DeSerializer(sock)

    def close(self):
        if self.socket is not None:
            self.socket.close()

    def _connect_socket(self):
        # create an INET, STREAMing socket
        self.socket = Socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        # now connect to the web server on port 80 - the normal http port
        self.socket.connect((self.ipaddress, self.port))

    def init_connection(self, extra_commands=[]):
        """init the socket connection then call the post_init method where to place custom
        initialization"""
        try:
            self._connect_socket()
            self.post_init(extra_commands)
            self.connected = True

            self.poll_connection()
            #self.timer.start()

        except ConnectionRefusedError as e:
            self.not_connected(e)
            self.connected = False

    def poll_connection(self):
        while True:
            try:
                ready_to_read, ready_to_write, in_error = \
                    select.select([self.socket.socket], [self.socket.socket], [self.socket.socket], 0)

                if len(ready_to_read) != 0:
                    self.ready_to_read()

                if len(in_error) != 0:
                    self.ready_with_error()

                if len(ready_to_write) != 0:
                    self.ready_to_write()

                QtWidgets.QApplication.processEvents()

            except Exception as e:
                self.process_error_in_polling(e)
                break

    def not_connected(self, e: ConnectionRefusedError):
        raise NotImplementedError

    def ready_to_read(self):
        """Do stuff (like read data) when messages arrive through the socket"""
        raise NotImplementedError

    def ready_to_write(self):
        """Send stuff into the socket"""
        raise NotImplementedError

    def ready_with_error(self):
        """Error in the socket communication"""
        raise NotImplementedError

    def process_error_in_polling(self, e: Exception):
        raise NotImplementedError

    def post_init(self, extra_commands=[]):
        """To implement in a real object implementation"""
        raise NotImplementedError


class TCPClient(TCPClientTemplate, QObject):
    """
    PyQt5 object initializing a TCP socket client. Can be used by any module but is a builtin functionality of all
    actuators and detectors of PyMoDAQ

    The module should init TCPClient, move it in a thread and communicate with it using a custom signal connected to
    TCPClient.queue_command slot. The module should also connect TCPClient.cmd_signal to one of its methods inorder to
    get info/data back from the client

    The client itself communicate with a TCP server, it is best to use a server object subclassing the TCPServer
    class defined within this python module

    Parameters
    ----------
    params_state: (dict) state of the Parameter settings of the module instantiating this client and wishing to
                    export its settings to the server. Obtained from param.saveState() where param is an
                    instance of Parameter object, see pyqtgraph.parametertree::Parameter

    """
    cmd_signal = Signal(ThreadCommand)  # signal to connect with a module slot in order to start communication back
    params = []

    def __init__(self, ipaddress="192.168.1.62", port=6341, params_state=None,
                 client_type="GRABBER"):
        """Create a socket client particularly fit to be used with PyMoDAQ's TCPServer

        Parameters
        ----------
        ipaddress: (str) the IP address of the server
        port: (int) the port where to communicate with the server
        params_state: (dict) state of the Parameter settings of the module instantiating this client and wishing to
                            export its settings to the server. Obtained from param.saveState() where param is an
                            instance of Parameter object, see pyqtgraph.parametertree::Parameter
        client_type: (str) should be one of the accepted client_type by the TCPServer instance (within pymodaq it is
                            either 'GRABBER' or 'ACTUATOR'
        """
        QObject.__init__(self)
        TCPClientTemplate.__init__(self, ipaddress, port, client_type)

        self.settings = Parameter.create(name='Settings', type='group', children=self.params)
        if params_state is not None:
            if isinstance(params_state, dict):
                self.settings.restoreState(params_state)
            elif isinstance(params_state, Parameter):
                self.settings.restoreState(params_state.saveState())

    def send_data(self, data: DataToExport):
        # first send 'Done' and then send the length of the list
        if not isinstance(data, DataToExport):
            raise TypeError(f'should send a DataToExport object')
        if self.socket is not None:
            self.socket.check_sended_with_serializer('Done')
            self.socket.check_sended_with_serializer(data)

    def send_infos_xml(self, infos: str):
        if self.socket is not None:
            self.socket.check_sended_with_serializer('Infos')
            self.socket.check_sended_with_serializer(infos)

    def send_info_string(self, info_to_display, value_as_string):
        if self.socket is not None:
            self.socket.check_sended_with_serializer('Info')
            self.socket.check_sended_with_serializer(info_to_display)  # the actual info to display as a string
            if not isinstance(value_as_string, str):
                value_as_string = str(value_as_string)
            self.socket.check_sended_with_serializer(value_as_string)

    @Slot(ThreadCommand)
    def queue_command(self, command=ThreadCommand):
        """
        when this TCPClient object is within a thread, the corresponding module communicate with it with signal and slots
        from module to client: module_signal to queue_command slot
        from client to module: self.cmd_signal to a module slot
        """
        if command.command == "ini_connection":
            status = self.init_connection()

        elif command.command == "quit":
            try:
                self.socket.close()
            except Exception as e:
                pass
            finally:
                self.cmd_signal.emit(ThreadCommand('disconnected'))

        elif command.command == 'update_connection':
            self.ipaddress = command.attribute['ipaddress']
            self.port = command.attribute['port']

        elif command.command == 'data_ready':
            self.data_ready(command.attribute)

        elif command.command == 'send_info':
            if self.socket is not None:
                path = command.attribute['path']
                param = command.attribute['param']

                self.socket.check_sended_with_serializer('Info_xml')
                self.socket.check_sended_with_serializer(path)

                # send value
                data = ioxml.parameter_to_xml_string(param)
                self.socket.check_sended_with_serializer(data)

        elif command.command == 'position_is':
            if self.socket is not None:
                self.socket.check_sended_with_serializer('position_is')
                self.socket.check_sended_with_serializer(command.attribute)

        elif command.command == 'move_done':
            if self.socket is not None:
                self.socket.check_sended_with_serializer('move_done')
                self.socket.check_sended_with_serializer(command.attribute)

        elif command.command == 'x_axis':
            raise DeprecationWarning('Getting axis though TCPIP is deprecated use the data objects directly')

        elif command.command == 'y_axis':
            raise DeprecationWarning('Getting axis though TCPIP is deprecated use the data objects directly')
        else:
            raise IOError('Unknown TCP client command')

    def not_connected(self, e):
        self.connected = False
        self.cmd_signal.emit(ThreadCommand('disconnected'))
        self.cmd_signal.emit(ThreadCommand('Update_Status', [getLineInfo() + str(e), 'log']))

    def ready_to_read(self):
        message = self._deserializer.string_deserialization()
        self.get_data(message)

    def ready_to_write(self):
        pass

    def ready_with_error(self):
        self.connected = False
        self.cmd_signal.emit(ThreadCommand('disconnected'))

    def process_error_in_polling(self, e: Exception):
        try:
            self.cmd_signal.emit(ThreadCommand('Update_Status', [getLineInfo() + str(e), 'log']))
            self.socket.check_sended_with_serializer('Quit')
            self.socket.close()
        except Exception:  # pragma: no cover
            pass

    def post_init(self, extra_commands=[]):

        self.cmd_signal.emit(ThreadCommand('connected'))
        self.socket.check_sended_with_serializer(self.client_type)

        self.send_infos_xml(ioxml.parameter_to_xml_string(self.settings))
        for command in extra_commands:
            if isinstance(command, ThreadCommand):
                self.cmd_signal.emit(command)

    def get_data(self, message: str):
        """

        Parameters
        ----------
        message

        Returns
        -------

        """
        if self.socket is not None:
            messg = ThreadCommand(message)

            if message == 'set_info':
                path = self._deserializer.list_deserialization()
                param_xml = self._deserializer.string_deserialization()
                messg.attribute = [path, param_xml]

            elif message == 'move_abs' or message == 'move_rel':
                position = self._deserializer.dwa_deserialization()
                messg.attribute = [position]

            self.cmd_signal.emit(messg)

    def data_ready(self, data: DataToExport):
        self.send_data(data)


class TCPServer(QObject):
    """
    Abstract class to be used as inherited by DAQ_Viewer_TCP or DAQ_Move_TCP
    """

    def __init__(self, client_type='GRABBER'):
        QObject.__init__(self)
        self.serversocket: Socket = None
        self.connected_clients = []
        self.listening = True
        self.processing = False
        self.client_type = client_type

    def close_server(self):
        """
            close the current opened server.
            Update the settings tree consequently.

            See Also
            --------
            set_connected_clients_table, daq_utils.ThreadCommand
        """
        server_socket = self.find_socket_within_connected_clients('server')
        self.remove_client(server_socket)

    def init_server(self):
        self.emit_status(ThreadCommand("Update_Status", [
            "Started new server for {:s}:{:d}".format(self.settings['socket_ip'],
                                                      self.settings['port_id']), 'log']))
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serversocket = Socket(serversocket)
        # bind the socket to a public host, and a well-known port
        try:
            self.serversocket.bind(
                (self.settings['socket_ip'], self.settings['port_id']))
            # self.serversocket.bind((socket.gethostname(), self.settings.child(('port_id')).value()))
        except socket.error as msg:
            self.emit_status(ThreadCommand("Update_Status",
                                           ['Bind failed. Error Code : ' + str(msg.errno) + ' Message ' + msg.strerror,
                                            'log']))
            raise ConnectionError('Bind failed. Error Code : ' + str(msg.errno) + ' Message ' + msg.strerror)

        self.serversocket.listen(1)
        self.connected_clients.append(dict(socket=self.serversocket, type='server'))
        self.settings.child('conn_clients').setValue(self.set_connected_clients_table())

        self.timer = self.startTimer(100)  # Timer event fired every 100ms
        # self.listen_client()

    def timerEvent(self, event):
        """
            Called by set timers.
            If the process is free, start the listen_client function.

            =============== ==================== ==============================================
            **Parameters**   **Type**              **Description**

            *event*          QTimerEvent object    Containing id from timer issuing this event
            =============== ==================== ==============================================

            See Also
            --------
            listen_client
        """
        if not self.processing:
            self.listen_client()

    def find_socket_within_connected_clients(self, client_type) -> Socket:
        """
            Find a socket from a connected client with socket type corresponding.

            =============== =========== ================================
            **Parameters**    **Type**    **Description**
            *client_type*      string     The corresponding client type
            =============== =========== ================================

            Returns
            -------
            dictionnary
                the socket dictionnary
        """
        res = None
        for socket_dict in self.connected_clients:
            if socket_dict['type'] == client_type:
                res = socket_dict['socket']
        return res

    def find_socket_type_within_connected_clients(self, sock):
        """
            Find a socket type from a connected client with socket content corresponding.

            =============== =========== ===================================
            **Parameters**    **Type**   **Description**
            *sock*             ???       The socket content corresponding.
            =============== =========== ===================================

            Returns
            -------
            dictionnary
                the socket dictionnary
        """
        res = None
        for socket_dict in self.connected_clients:
            if socket_dict['socket'] == sock:
                res = socket_dict['type']
        return res

    def set_connected_clients_table(self):
        """

        """
        con_clients = OrderedDict()
        for socket_dict in self.connected_clients:
            try:
                address = str(socket_dict['socket'].getsockname())
            except Exception:
                address = "unconnected invalid socket"
            con_clients[socket_dict['type']] = address
        return con_clients

    @Slot(list)
    def print_status(self, status):
        """
            Print the given status.

            =============== ============= ================================================
            **Parameters**    **Type**       **Description**
            *status*          string list    a string list representing the status socket
            =============== ============= ================================================
        """
        print(status)

    def remove_client(self, sock):
        sock_type = self.find_socket_type_within_connected_clients(sock)
        if sock_type is not None:
            self.connected_clients.remove(dict(socket=sock, type=sock_type))
            self.settings.child('conn_clients').setValue(self.set_connected_clients_table())
            try:
                sock.close()
            except Exception:
                pass
            self.emit_status(ThreadCommand("Update_Status", ['Client ' + sock_type + ' disconnected', 'log']))

    def select(self, rlist, wlist=[], xlist=[], timeout=0):
        """
        Implements the select method, https://docs.python.org/3/library/select.html
        Parameters
        ----------
        rlist: (list) wait until ready for reading
        wlist: (list) wait until ready for writing
        xlist: (list)  wait for an “exceptional condition”
        timeout: (float) optional timeout argument specifies a time-out as a floating point number in seconds.
                When the timeout argument is omitted the function blocks until at least one file descriptor is ready.
                A time-out value of zero specifies a poll and never blocks.

        Returns
        -------
        list: readable sockets
        list: writable sockets
        list: sockets with error pending
        """

        read_sockets, write_sockets, error_sockets = select.select([sock.socket for sock in rlist],
                                                                   [sock.socket for sock in wlist],
                                                                   [sock.socket for sock in xlist],
                                                                   timeout)

        return ([Socket(sock) for sock in read_sockets], [Socket(sock) for sock in write_sockets],
                [Socket(sock) for sock in error_sockets])

    def listen_client(self):
        """
            Server function.
            Used to connect or listen incoming message from a client.
        """
        try:
            self.processing = True
            # QtWidgets.QApplication.processEvents() #to let external commands in
            read_sockets, write_sockets, error_sockets = self.select(
                [client['socket'] for client in self.connected_clients], [],
                [client['socket'] for client in self.connected_clients],
                0)
            for sock in error_sockets:
                self.remove_client(sock)

            for sock in read_sockets:
                QThread.msleep(100)
                if sock == self.serversocket:  # New connection
                    # means a new socket (client) try to reach the server
                    (client_socket, address) = self.serversocket.accept()
                    DAQ_type = DeSerializer(client_socket).string_deserialization()
                    if DAQ_type not in self.socket_types:
                        self.emit_status(ThreadCommand("Update_Status", [DAQ_type + ' is not a valid type', 'log']))
                        client_socket.close()
                        break

                    self.connected_clients.append(dict(socket=client_socket, type=DAQ_type))
                    self.settings.child('conn_clients').setValue(self.set_connected_clients_table())
                    self.emit_status(ThreadCommand("Update_Status",
                                                   [DAQ_type + ' connected with ' + address[0] + ':' + str(address[1]),
                                                    'log']))
                    QtWidgets.QApplication.processEvents()

                else:  # Some incoming message from a client
                    # Data received from client, process it
                    try:
                        message = DeSerializer(sock).string_deserialization()
                        if message in ['Done', 'Info', 'Infos', 'Info_xml', 'position_is', 'move_done']:
                            self.process_cmds(message, command_sock=None)
                        elif message == 'Quit':
                            raise Exception("socket disconnect by user")
                        else:
                            self.process_cmds(message, command_sock=sock)

                    # client disconnected, so remove from socket list
                    except Exception as e:
                        self.remove_client(sock)

            self.processing = False

        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status", [str(e), 'log']))

    def send_command(self, sock: Socket, command="move_at"):
        """
            Send one of the message contained in self.message_list toward a socket with identity socket_type.
            First send the length of the command with 4bytes.

            =============== =========== ==========================
            **Parameters**    **Type**    **Description**
            *sock*             ???        The current socket
            *command*         string      The command as a string
            =============== =========== ==========================

            See Also
            --------
            utility_classes.DAQ_Viewer_base.emit_status, daq_utils.ThreadCommand, message_to_bytes
        """
        if command not in self.message_list:
            self.emit_status(
                ThreadCommand("Update_Status", [f'Command: {command} is not in the specified list: {self.message_list}',
                                                'log']))
            return

        if sock is not None:
            sock.check_sended_with_serializer(command)

    def emit_status(self, status):
        print(status)

    def read_data(self, sock):
        pass

    def send_data(self, sock, data):
        pass

    def command_done(self, command_sock):
        pass

    def command_to_from_client(self, command):
        pass

    def process_cmds(self, command, command_sock=None):
        """
            Process the given command.
        """
        if command not in self.message_list:
            self.emit_status(
                ThreadCommand("Update_Status", [f'Command: {command} is not in the specified list: {self.message_list}',
                                                'log']))
            return

        if command == 'Done':  # means the given socket finished grabbing data and is ready to send them
            self.command_done(command_sock)

        elif command == "Infos":
            """replace entirely the client settings information on the server widget
            should be done as the init of the client module"""
            try:
                sock = self.find_socket_within_connected_clients(self.client_type)
                if sock is not None:  # if client self.client_type is connected then send it the command
                    self.read_infos(sock)

            except Exception as e:
                self.emit_status(ThreadCommand("Update_Status", [str(e), 'log']))

        elif command == 'Info_xml':
            """update the state of one of the client settings on the server widget"""
            sock = self.find_socket_within_connected_clients(self.client_type)
            if sock is not None:
                self.read_info_xml(sock)

        elif command == "Info":
            # add a custom info (as a string value) in the server widget settings. To be used if the client is not a
            # PyMoDAQ's module

            try:
                sock = self.find_socket_within_connected_clients(self.client_type)
                if sock is not None:  # if client self.client_type is connected then send it the command
                    self.read_info(sock)
            except Exception as e:
                self.emit_status(ThreadCommand("Update_Status", [str(e), 'log']))

        else:
            self.command_to_from_client(command)

    def read_infos(self, sock: Socket = None, infos=''):
        if sock is not None:
            infos = DeSerializer(sock).string_deserialization()
        params = ioxml.XML_string_to_parameter(infos)

        param_state = {'title': 'Infos Client:', 'name': 'settings_client', 'type': 'group', 'children': params}
        self.settings.child('settings_client').restoreState(param_state)

    def read_info_xml(self, sock: Socket, path=['settings', 'apathinsettings'], param_xml=''):
        if sock is not None:
            deser = DeSerializer(sock)
            path = deser.list_deserialization()
            param_xml = deser.string_deserialization()
        try:
            param_dict = ioxml.XML_string_to_parameter(param_xml)[0]
        except Exception as e:
            raise Exception(f'Invalid xml structure for TCP server settings: {str(e)}')
        try:
            param_here = self.settings.child('settings_client', *path[1:])
        except Exception as e:
            raise Exception(f'Invalid path for TCP server settings: {str(e)}')
        param_here.restoreState(param_dict)

    def read_info(self, sock: Socket=None, test_info='an_info', test_value=''):
        """
        if the client is not from PyMoDAQ it can use this method to display some info into the server widget
        """
        # #first get the info type
        if sock is None:
            info = test_info
            data = test_value
        else:
            deser = DeSerializer(sock)
            info = deser.string_deserialization()
            data = deser.string_deserialization()

        if info not in putils.iter_children(self.settings.child('infos'), []):
            self.settings.child('infos').addChild({'name': info, 'type': 'str', 'value': data})
            pass
        else:
            self.settings.child('infos', info).setValue(data)


class MockServer(TCPServer):
    params = []

    def __init__(self, client_type='GRABBER'):
        super().__init__(client_type)

        self.settings = Parameter.create(name='settings', type='group', children=tcp_parameters)


class MockDataGrabber:

    def __init__(self, grabber_dim='2D'):
        super().__init__()
        self.Nx = 256
        self.Ny = 128
        self.x_axis = np.linspace(0, self.Nx-1, self.Nx)
        self.y_axis = np.linspace(0, self.Ny-1, self.Ny)
        self.grabber_dim = grabber_dim

    def grab(self) -> List[DataFromPlugins]:
        if self.grabber_dim == '0D':
            return [DataFromPlugins(data=[np.array([np.random.rand()])])]

        elif self.grabber_dim == '1D':
            return [DataFromPlugins(data=[mutils.gauss1D(self.x_axis, 128, 25) +
                                          np.random.rand(self.Nx)])]

        elif self.grabber_dim == '2D':
            return [DataFromPlugins(data=[mutils.gauss2D(self.x_axis, 128, 65,
                                                         self.y_axis, 60, 10) +
                                          np.random.rand(self.Ny, self.Nx)])]


class Grabber(QObject):
    command_tcpip = Signal(ThreadCommand)

    def __init__(self, grab_method=None):
        super().__init__()
        self.send_to_tcpip = False
        self.grab_method = grab_method

    def connect_tcp_ip(self, ip='localhost', port=6341):
        self.tcpclient_thread = QThread()
        tcpclient = TCPClient(ip, port=port)

        tcpclient.moveToThread(self.tcpclient_thread)
        self.tcpclient_thread.tcpclient = tcpclient
        tcpclient.cmd_signal.connect(self.process_tcpip_cmds)

        self.command_tcpip[ThreadCommand].connect(tcpclient.queue_command)

        self.tcpclient_thread.start()
        #tcpclient.init_connection(extra_commands=[ThreadCommand('get_axis', )])
        tcpclient.init_connection()
        self.send_to_tcpip = True

    def snapshot(self, info='', send_to_tcpip=True):
        self.grab_data()

    def grab_data(self):
        """
            Do a grab session using 2 profile :
                * if grab pb checked do  a continous save and send an "update_channels" thread command and a "grab" too.
                * if not send a "stop_grab" thread command with settings "main settings-naverage" node value as an attribute.

            See Also
            --------
            daq_utils.ThreadCommand, set_enabled_Ini_buttons
        """
        data = self.grab_method()
        self.command_tcpip.emit(ThreadCommand('data_ready', data))

    @Slot(ThreadCommand)
    def process_tcpip_cmds(self, status):
        if 'Send Data' in status.command:
            self.snapshot('', send_to_tcpip=True)

        elif status.command == 'connected':
            #self.settings.child('main_settings', 'tcpip', 'tcp_connected').setValue(True)
            pass

        elif status.command == 'disconnected':
            #self.settings.child('main_settings', 'tcpip', 'tcp_connected').setValue(False)
            pass

        elif status.command == 'Update_Status':
            print(status)


if __name__ == '__main__':  # pragma: no cover
    import sys
    app = QtWidgets.QApplication(sys.argv)
    mockdata_grabber = MockDataGrabber('2D')
    grabber = Grabber(mockdata_grabber.grab)
    grabber.connect_tcp_ip()

    sys.exit(app.exec_())
