# -*- coding: utf-8 -*-
"""
Created on Fri Aug 30 12:21:56 2019

@author: Weber
"""
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QThread
from PyQt5 import QtWidgets
import socket
import select
import numpy as np

import pymodaq.daq_utils.parameter.ioxml
import pymodaq.daq_utils.parameter.utils
import pymodaq.daq_utils.parameter.pymodaq_ptypes
from pymodaq.daq_utils.daq_utils import getLineInfo, ThreadCommand, load_config
from pyqtgraph.parametertree import Parameter
from collections import OrderedDict

config = load_config()

tcp_parameters = [
    {'title': 'Port:', 'name': 'port_id', 'type': 'int', 'value': config['network']['tcp-server']['port'], },
    {'title': 'IP:', 'name': 'socket_ip', 'type': 'str', 'value': config['network']['tcp-server']['ip'], },
    {'title': 'Settings PyMoDAQ Client:', 'name': 'settings_client', 'type': 'group', 'children': []},
    {'title': 'Infos Client:', 'name': 'infos', 'type': 'group', 'children': []},
    {'title': 'Connected clients:', 'name': 'conn_clients', 'type': 'table',
     'value': dict(), 'header': ['Type', 'adress']}, ]


class Socket:
    def __init__(self, socket=None):
        super().__init__()
        self._socket = socket

    def __eq__(self, other_obj):
        if isinstance(other_obj, Socket):
            other_obj = other_obj.socket
        return self.socket == other_obj

    @property
    def socket(self):
        return self._socket

    def bind(self, *args, **kwargs):
        return self.socket.bind(*args, **kwargs)

    def listen(self, *args, **kwargs):
        return self.socket.listen(*args, **kwargs)

    def getsockname(self, *args, **kwargs):
        return self.socket.getsockname(*args, **kwargs)

    def accept(self):
        sock, addr = self.socket.accept()
        return Socket(sock), addr

    def connect(self, *args, **kwargs):
        return self.socket.connect(*args, **kwargs)

    def send(self, *args, **kwargs):
        return self.socket.send(*args, **kwargs)

    def sendall(self, *args, **kwargs):
        return self.socket.sendall(*args, **kwargs)

    def recv(self, *args, **kwargs):
        return self.socket.recv(*args, **kwargs)

    def close(self):
        return self.socket.close()

    @classmethod
    def message_to_bytes(cls, message):
        """
        Convert a string to a byte array
        Parameters
        ----------
        message (str): message

        Returns
        -------
        Tuple consisting of the message converted as a byte array, and the length of the byte array, itself as a byte array of length 4
        """

        if not isinstance(message, str) and not isinstance(message, bytes):
            message = str(message)
        if not isinstance(message, bytes):
            message = message.encode()
        return message, cls.int_to_bytes(len(message))

    @classmethod
    def int_to_bytes(cls, an_integer):
        if not isinstance(an_integer, int):
            raise TypeError(f'{an_integer} should be an integer, not a {type(an_integer)}')
        return an_integer.to_bytes(4, 'big')

    @classmethod
    def bytes_to_int(cls, bytes_string):
        if not isinstance(bytes_string, bytes):
            raise TypeError(f'{bytes_string} should be an bytes string, not a {type(bytes_string)}')
        assert len(bytes_string) == 4
        return int.from_bytes(bytes_string, 'big')

    def check_sended(self, data_bytes):
        """
        Make sure all bytes are sent through the socket
        Parameters
        ----------
        socket
        data_bytes

        Returns
        -------

        """
        if not isinstance(data_bytes, bytes):
            raise TypeError(f'{data_bytes} should be an bytes string, not a {type(data_bytes)}')
        sended = 0
        while sended < len(data_bytes):
            sended += self.socket.send(data_bytes[sended:])
        # print(data_bytes)

    def check_received_length(self, length):
        """
        Make sure all bytes (length) that should be received are received through the socket
        Parameters
        ----------
        sock
        length

        Returns
        -------

        """
        if not isinstance(length, int):
            raise TypeError(f'{length} should be an integer, not a {type(length)}')

        mess_length = 0
        data_bytes = b''
        while mess_length < length:
            if mess_length < length - 4096:
                data_bytes_tmp = self.socket.recv(4096)
            else:
                data_bytes_tmp = self.socket.recv(length - mess_length)
            mess_length += len(data_bytes_tmp)
            data_bytes += data_bytes_tmp
        # print(data_bytes)
        return data_bytes

    def send_string(self, string):
        """

        Parameters
        ----------
        socket
        string

        Returns
        -------

        """
        cmd_bytes, cmd_length_bytes = self.message_to_bytes(string)
        self.check_sended(cmd_length_bytes)
        self.check_sended(cmd_bytes)

    def get_string(self):
        string_len = self.get_int()
        string = self.check_received_length(string_len).decode()
        return string

    def get_int(self):
        data = self.bytes_to_int(self.check_received_length(4))
        return data

    def send_scalar(self, data):
        """
        Convert it to numpy array then send the data type, the data_byte length and finally the data_bytes
        Parameters
        ----------
        data

        Returns
        -------

        """
        if not (isinstance(data, int) or isinstance(data, float)):
            raise TypeError(f'{data} should be an integer or a float, not a {type(data)}')
        data = np.array([data])
        data_type = data.dtype.descr[0][1]
        data_bytes = data.tobytes()
        self.send_string(data_type)
        self.check_sended(self.int_to_bytes(len(data_bytes)))
        self.check_sended(data_bytes)

    def get_scalar(self):
        """

        Parameters
        ----------
        socket

        Returns
        -------

        """
        data_type = self.get_string()
        data_len = self.get_int()
        data_bytes = self.check_received_length(data_len)

        data = np.frombuffer(data_bytes, dtype=data_type)[0]
        return data

    def get_array(self):
        """get 1D or 2D arrays"""
        data_type = self.get_string()
        data_len = self.get_int()
        shape_len = self.get_int()
        shape = []
        for ind in range(shape_len):
            shape.append(self.get_int())
        data_bytes = self.check_received_length(data_len)
        data = np.frombuffer(data_bytes, dtype=data_type)
        data = data.reshape(tuple(shape))
        return data

    def send_array(self, data_array):
        """send ndarrays

        get data type as a string
        reshape array as 1D array and get the array dimensionality (len of array's shape)
        convert Data array as bytes
        send data type
        send data length
        send data shape length
        send all values of the shape as integers converted to bytes
        send data as bytes
        """
        if not isinstance(data_array, np.ndarray):
            raise TypeError(f'{data_array} should be an numpy array, not a {type(data_array)}')
        data_type = data_array.dtype.descr[0][1]
        data_shape = data_array.shape

        data = data_array.reshape(np.prod(data_shape))
        data_bytes = data.tobytes()

        self.send_string(data_type)
        self.check_sended(self.int_to_bytes(len(data_bytes)))
        self.check_sended(self.int_to_bytes(len(data_shape)))
        for Nxxx in data_shape:
            self.check_sended(self.int_to_bytes(Nxxx))
        self.check_sended(data_bytes)

    def send_list(self, data_list):
        """

        Parameters
        ----------
        socket
        data_list

        Returns
        -------

        """
        if not isinstance(data_list, list):
            raise TypeError(f'{data_list} should be a list, not a {type(data_list)}')
        self.check_sended(self.int_to_bytes(len(data_list)))
        for data in data_list:

            if isinstance(data, np.ndarray):
                self.send_string('array')
                self.send_array(data)

            elif isinstance(data, str):
                self.send_string('string')
                self.send_string(data)

            elif isinstance(data, int) or isinstance(data, float):
                self.send_string('scalar')
                self.send_scalar(data)

            else:
                raise TypeError(f'the element {data} type is cannot be sent by TCP/IP, only numpy arrays'
                                f', strings, or scalars (int or float)')

    def get_list(self):
        """
        Receive data from socket as a list
        Parameters
        ----------
        socket: the communication socket
        Returns
        -------

        """
        data = []
        list_len = self.get_int()

        for ind in range(list_len):
            data_type = self.get_string()
            if data_type == 'scalar':
                data.append(self.get_scalar())
            elif data_type == 'string':
                data.append(self.get_string())
            elif data_type == 'array':
                data.append(self.get_array())
        return data


class TCPClient(QObject):
    """
    PyQt5 object initializing a TCP socket client. Can be used by any module but is a builtin functionnality of all
    actuators and detectors of PyMoDAQ

    The module should init TCPClient, move it in a thread and communicate with it using a custom signal connected to
    TCPClient.queue_command slot. The module should also connect TCPClient.cmd_signal to one of its methods inorder to
    get info/data back from the client

    The client itself communicate with a TCP server, it is best to use a server object subclassing the TCPServer
    class defined within this python module

    """
    cmd_signal = pyqtSignal(ThreadCommand)  # signal to connect with a module slot in order to start communication back
    params = []

    def __init__(self, ipaddress="192.168.1.62", port=6341, params_state=None, client_type="GRABBER"):
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
        super().__init__()

        self.ipaddress = ipaddress
        self.port = port
        self._socket = None
        self.connected = False
        self.settings = Parameter.create(name='Settings', type='group', children=self.params)
        if params_state is not None:
            if isinstance(params_state, dict):
                self.settings.restoreState(params_state)
            elif isinstance(params_state, Parameter):
                self.settings.restoreState(params_state.saveState())

        self.client_type = client_type  # "GRABBER" or "ACTUATOR"

    @property
    def socket(self):
        return self._socket

    @socket.setter
    def socket(self, sock):
        self._socket = sock

    def close(self):
        if self.socket is not None:
            self.socket.close()

    def send_data(self, data_list):
        # first send 'Done' and then send the length of the list
        if self.socket is not None and isinstance(data_list, list):
            self.socket.send_string('Done')
            self.socket.send_list(data_list)

    def send_infos_xml(self, infos):
        if self.socket is not None:
            self.socket.send_string('Infos')
            self.socket.send_string(infos)

    def send_info_string(self, info_to_display, value_as_string):
        if self.socket is not None:
            self.socket.send_string('Info')  # the command
            self.socket.send_string(info_to_display)  # the actual info to display as a string
            if not isinstance(value_as_string, str):
                value_as_string = str(value_as_string)
            self.socket.send_string(value_as_string)

    @pyqtSlot(ThreadCommand)
    def queue_command(self, command=ThreadCommand()):
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
            self.ipaddress = command.attributes['ipaddress']
            self.port = command.attributes['port']

        elif command.command == 'data_ready':
            self.data_ready(command.attributes)

        elif command.command == 'send_info':
            if self.socket is not None:
                path = command.attributes['path']
                param = command.attributes['param']

                self.socket.send_string('Info_xml')
                self.socket.send_list(path)

                # send value
                data = pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_string(param)
                self.socket.send_string(data)

        elif command.command == 'position_is':
            if self.socket is not None:
                self.socket.send_string('position_is')
                self.socket.send_scalar(command.attributes[0])

        elif command.command == 'move_done':
            if self.socket is not None:
                self.socket.send_string('move_done')
                self.socket.send_scalar(command.attributes[0])

        elif command.command == 'x_axis':
            if self.socket is not None:
                self.socket.send_string('x_axis')
                x_axis = dict(label='', units='')
                if isinstance(command.attributes[0], np.ndarray):
                    x_axis['data'] = command.attributes[0]
                elif isinstance(command.attributes[0], dict):
                    x_axis.update(command.attributes[0].copy())

                self.socket.send_array(x_axis['data'])
                self.socket.send_string(x_axis['label'])
                self.socket.send_string(x_axis['units'])

        elif command.command == 'y_axis':
            if self.socket is not None:
                self.socket.send_string('y_axis')
                y_axis = dict(label='', units='')
                if isinstance(command.attributes[0], np.ndarray):
                    y_axis['data'] = command.attributes[0]
                elif isinstance(command.attributes[0], dict):
                    y_axis.update(command.attributes[0].copy())

                self.socket.send_array(y_axis['data'])
                self.socket.send_string(y_axis['label'])
                self.socket.send_string(y_axis['units'])

        else:
            raise IOError('Unknown TCP client command')

    def init_connection(self, extra_commands=[]):
        # %%
        try:
            # create an INET, STREAMing socket
            self.socket = Socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
            # now connect to the web server on port 80 - the normal http port
            self.socket.connect((self.ipaddress, self.port))
            self.cmd_signal.emit(ThreadCommand('connected'))
            self.socket.send_string(self.client_type)

            self.send_infos_xml(pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_string(self.settings))
            for command in extra_commands:
                if isinstance(command, ThreadCommand):
                    self.cmd_signal.emit(command)
            self.connected = True
            # %%

            while True:
                try:
                    ready_to_read, ready_to_write, in_error = \
                        select.select([self.socket.socket], [self.socket.socket], [self.socket.socket], 0)

                    if len(ready_to_read) != 0:
                        message = self.socket.get_string()
                        # print(message)
                        self.get_data(message)

                    if len(in_error) != 0:
                        self.connected = False
                        self.cmd_signal.emit(ThreadCommand('disconnected'))

                    QtWidgets.QApplication.processEvents()

                except Exception as e:
                    try:
                        self.cmd_signal.emit(ThreadCommand('Update_Status', [getLineInfo() + str(e), 'log']))
                        self.socket.send_string('Quit')
                        self.socket.close()
                    except Exception:  # pragma: no cover
                        pass
                    finally:
                        break

        except ConnectionRefusedError as e:
            self.connected = False
            self.cmd_signal.emit(ThreadCommand('disconnected'))
            self.cmd_signal.emit(ThreadCommand('Update_Status', [getLineInfo() + str(e), 'log']))

    def get_data(self, message):
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
                path = self.socket.get_list()
                param_xml = self.socket.get_string()
                messg.attributes = [path, param_xml]

            elif message == 'move_abs':
                position = self.socket.get_scalar()
                messg.attributes = [position]

            elif message == 'move_rel':
                position = self.socket.get_scalar()
                messg.attributes = [position]

            self.cmd_signal.emit(messg)

    @pyqtSlot(list)
    def data_ready(self, datas):
        self.send_data(datas[0]['data'])  # datas from viewer 0 and get 'data' key (within the ordereddict list of datas


class TCPServer(QObject):
    """
    Abstract class to be used as inherited by DAQ_Viewer_TCP or DAQ_Move_TCP
    """

    def __init__(self, client_type='GRABBER'):
        QObject.__init__(self)
        self.serversocket = None
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
            "Started new server for {:s}:{:d}".format(self.settings.child(('socket_ip')).value(),
                                                      self.settings.child(('port_id')).value()), 'log']))
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serversocket = Socket(serversocket)
        # bind the socket to a public host, and a well-known port
        try:
            self.serversocket.bind(
                (self.settings.child(('socket_ip')).value(), self.settings.child(('port_id')).value()))
            # self.serversocket.bind((socket.gethostname(), self.settings.child(('port_id')).value()))
        except socket.error as msg:
            self.emit_status(ThreadCommand("Update_Status",
                                           ['Bind failed. Error Code : ' + str(msg.errno) + ' Message ' + msg.strerror,
                                            'log']))
            raise ConnectionError('Bind failed. Error Code : ' + str(msg.errno) + ' Message ' + msg.strerror)

        self.serversocket.listen(1)
        self.connected_clients.append(dict(socket=self.serversocket, type='server'))
        self.settings.child(('conn_clients')).setValue(self.set_connected_clients_table())

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

    def find_socket_within_connected_clients(self, client_type):
        """
            Find a socket from a conneceted client with socket type corresponding.

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

    @pyqtSlot(list)
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
            self.settings.child(('conn_clients')).setValue(self.set_connected_clients_table())
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
                    DAQ_type = client_socket.get_string()
                    if DAQ_type not in self.socket_types:
                        self.emit_status(ThreadCommand("Update_Status", [DAQ_type + ' is not a valid type', 'log']))
                        client_socket.close()
                        break

                    self.connected_clients.append(dict(socket=client_socket, type=DAQ_type))
                    self.settings.child(('conn_clients')).setValue(self.set_connected_clients_table())
                    self.emit_status(ThreadCommand("Update_Status",
                                                   [DAQ_type + ' connected with ' + address[0] + ':' + str(address[1]),
                                                    'log']))
                    QtWidgets.QApplication.processEvents()

                else:  # Some incoming message from a client
                    # Data received from client, process it
                    try:
                        message = sock.get_string()
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

    def send_command(self, sock, command="move_at"):
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
            sock.send_string(command)

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

    def read_infos(self, sock=None, infos=''):
        if sock is not None:
            infos = sock.get_string()
        params = pymodaq.daq_utils.parameter.ioxml.XML_string_to_parameter(infos)

        param_state = {'title': 'Infos Client:', 'name': 'settings_client', 'type': 'group', 'children': params}
        self.settings.child(('settings_client')).restoreState(param_state)

    def read_info_xml(self, sock, path=['settings', 'apathinsettings'], param_xml=''):
        if sock is not None:
            path = sock.get_list()
            param_xml = sock.get_string()
        try:
            param_dict = pymodaq.daq_utils.parameter.ioxml.XML_string_to_parameter(param_xml)[0]
        except Exception as e:
            raise Exception(f'Invalid xml structure for TCP server settings: {str(e)}')
        try:
            param_here = self.settings.child('settings_client', *path[1:])
        except Exception as e:
            raise Exception(f'Invalid path for TCP server settings: {str(e)}')
        param_here.restoreState(param_dict)

    def read_info(self, sock=None, test_info='an_info', test_value=''):
        """
        if the client is not from PyMoDAQ it can use this method to display some info into the server widget
        """
        # #first get the info type
        if sock is None:
            info = test_info
            data = test_value
        else:
            info = sock.get_string()
            data = sock.get_string()

        if info not in pymodaq.daq_utils.parameter.utils.iter_children(self.settings.child(('infos')), []):
            self.settings.child('infos').addChild({'name': info, 'type': 'str', 'value': data})
            pass
        else:
            self.settings.child('infos', info).setValue(data)


class MockServer(TCPServer):
    params = []

    def __init__(self, client_type='GRABBER'):
        super().__init__(client_type)

        self.settings = Parameter.create(name='settings', type='group', children=tcp_parameters)


if __name__ == '__main__':  # pragma: no cover
    import sys

    app = QtWidgets.QApplication(sys.argv)
    server = MockServer()

    params = [{'name': 'detsettings', 'type': 'group', 'children': [
        {'title': 'Device index:', 'name': 'device', 'type': 'int', 'value': 0, 'max': 3, 'min': 0},
        {'title': 'Infos:', 'name': 'infos', 'type': 'str', 'value': "one_info", 'readonly': True},
        {'title': 'Line Settings:', 'name': 'line_settings', 'type': 'group', 'expanded': False,
         'children': [
             {'title': 'Device index:', 'name': 'device1', 'type': 'int', 'value': 0, 'max': 3,
              'min': 0},
             {'title': 'Device index:', 'name': 'device2', 'type': 'int', 'value': 0, 'max': 3,
              'min': 0}, ]
         }]}]

    param = Parameter.create(name='settings', type='group', children=params)
    params = pymodaq.daq_utils.parameter.ioxml.parameter_to_xml_string(param)
    server.read_infos(None, params)
    sys.exit(app.exec_())
