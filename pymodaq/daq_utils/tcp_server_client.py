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
from pymodaq.daq_utils.daq_utils import check_received_length, ThreadCommand, \
    getLineInfo, send_scalar, send_string, send_list, get_scalar, get_int, get_string, send_array
from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import pymodaq.daq_utils.custom_parameter_tree as custom_tree
from collections import OrderedDict

tcp_parameters = [{'title': 'Port:', 'name': 'port_id', 'type': 'int', 'value': 6341, 'default': 6341},
                                 {'title': 'IP:', 'name': 'socket_ip', 'type': 'str', 'value': 'localhost',
                                  'default': '10.47.1.33'},
                                 {'title': 'Infos Client:', 'name': 'infos', 'type': 'group', 'children': []},
                                 {'title': 'Connected clients:', 'name': 'conn_clients', 'type': 'table',
                                  'value': dict(), 'header': ['Type', 'adress']},]
# %%

class TCPClient(QObject):
    cmd_signal = pyqtSignal(ThreadCommand)
    params = []

    def __init__(self, parent=None, ipaddress="192.168.1.62", port=6341, params_state=None, client_type="GRABBER"):
        super().__init__()

        self.ipaddress = ipaddress
        self.port = port

        self.settings = Parameter.create(name='Settings', type='group', children=self.params)
        if params_state is not None:
            if isinstance(params_state, dict):
                self.settings.restoreState(params_state)
            elif isinstance(params_state, Parameter):
                self.settings.restoreState(params_state.saveState())

        self.parent = parent
        self.socket = None
        self.client_type = client_type #"GRABBER" or "ACTUATOR"

    def send_data(self, data_list):
        # first send 'Done' and then send the length of the list
        send_string(self.socket, 'Done')
        send_list(self.socket, data_list)



    def send_infos_xml(self, infos):
        send_string(self.socket, 'Infos')
        send_string(self.socket, infos)


    @pyqtSlot(ThreadCommand)
    def queue_command(self, command=ThreadCommand()):
        """

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
            path = command.attributes['path']
            param = command.attributes['param']

            param_xml = custom_tree.parameter_to_xml_string(param)

            send_string(self.socket, 'Info_xml')
            send_list(self.socket, path)

            # send value
            data = custom_tree.parameter_to_xml_string(param)
            send_string(self.socket, data)

        elif command.command == 'position_is':
            send_string(self.socket, 'position_is')
            send_scalar(self.socket, command.attributes[0])

        elif command.command == 'move_done':
            send_string(self.socket, 'move_done')
            send_scalar(self.socket, command.attributes[0])

        elif command.command == 'x_axis':
            send_string(self.socket, 'x_axis')
            x_axis = dict(label='', units='')
            if isinstance(command.attributes[0], np.ndarray):
                x_axis['data'] = command.attributes[0]
            elif isinstance(command.attributes[0], dict):
                x_axis.update(command.attributes[0].copy())

            send_array(self.socket, x_axis['data'])
            send_string(self.socket, x_axis['label'])
            send_string(self.socket, x_axis['units'])

        elif command.command == 'y_axis':
            send_string(self.socket, 'y_axis')
            y_axis = dict(label='', units='')
            if isinstance(command.attributes[0], np.ndarray):
                y_axis['data'] = command.attributes[0]
            elif isinstance(command.attributes[0], dict):
                y_axis.update(command.attributes[0].copy())

            send_array(self.socket, y_axis['data'])
            send_string(self.socket, y_axis['label'])
            send_string(self.socket, y_axis['units'])


    def init_connection(self):
        # %%
        try:
            # create an INET, STREAMing socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # now connect to the web server on port 80 - the normal http port
            self.socket.connect((self.ipaddress, self.port))
            self.cmd_signal.emit(ThreadCommand('connected'))
            send_string(self.socket, self.client_type)

            self.send_infos_xml(custom_tree.parameter_to_xml_string(self.settings))
            self.cmd_signal.emit(ThreadCommand('get_axis'))
            # %%
            while True:

                try:
                    ready_to_read, ready_to_write, in_error = \
                        select.select([self.socket], [self.socket], [self.socket], 0)

                    if len(ready_to_read) != 0:
                        message = get_string(self.socket)
                        # print(message)
                        self.get_data(message)

                    if len(in_error) != 0:
                        self.cmd_signal.emit(ThreadCommand('disconnected'))

                    QtWidgets.QApplication.processEvents()

                except Exception as e:
                    try:
                        self.cmd_signal.emit(ThreadCommand('Update_Status', [getLineInfo() + str(e), 'log']))
                        send_string(self.socket, 'Quit')
                        self.socket.close()
                    except:
                        pass
                    finally:
                        break

        except ConnectionRefusedError as e:
            self.cmd_signal.emit(ThreadCommand('disconnected'))
            self.cmd_signal.emit(ThreadCommand('Update_Status', [getLineInfo() + str(e), 'log']))

    # %%
    def get_data(self, message):
        """

        Parameters
        ----------
        message

        Returns
        -------

        """
        messg = ThreadCommand(message)

        if message == 'set_info':
            list_len = get_int(self.socket)
            path = []
            for ind in range(list_len):
                path.append(get_string(self.socket))
            param_xml = get_string(self.socket)
            messg.attributes = [path, param_xml]

        elif message == 'move_abs':
            position = get_scalar(self.socket)
            messg.attributes = [position]

        elif message == 'move_rel':
            position = get_scalar(self.socket)
            messg.attributes = [position]

        self.cmd_signal.emit(messg)

        # data = 100 * np.random.rand(100, 200)
        # self.data_ready([data.astype(np.int)])






    @pyqtSlot(list)
    def data_ready(self, datas):
        self.send_data(datas[0]['data'])  # datas from viewer 0 and get 'data' key (within the ordereddict list of datas


class TCPServer(QObject):
    """
    Abstract class to be used as inherited by DAQ_Viewer_TCP or DAQ_Move_TCP
    """
    def __init__(self, client_type='GRABBER'):
        QObject.__init__(self)

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
        for sock_dict in self.connected_clients:
            try:
                sock_dict['socket'].close()
            except:
                pass
        self.connected_clients = []
        self.settings.child(('conn_clients')).setValue(self.set_connected_clients_table())

    def init_server(self):
        self.emit_status(ThreadCommand("Update_Status", [
            "Started new server for {:s}:{:d}".format(self.settings.child(('socket_ip')).value(),
                                                      self.settings.child(('port_id')).value()), 'log']))
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # bind the socket to a public host, and a well-known port
        try:
            # self.serversocket.bind((self.settings.child(('socket_ip')).value(),self.settings.child(('port_id')).value()))
            self.serversocket.bind((socket.gethostname(), self.settings.child(('port_id')).value()))
        except socket.error as msg:
            self.emit_status(ThreadCommand("Update_Status",
                                           ['Bind failed. Error Code : ' + str(msg.errno) + ' Message ' + msg.strerror,
                                            'log']))
            raise Exception('Bind failed. Error Code : ' + str(msg.errno) + ' Message ' + msg.strerror)

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

    def set_connected_clients_table(self):
        """

        """
        con_clients = OrderedDict()
        for socket_dict in self.connected_clients:
            try:
                address = str(socket_dict['socket'].getsockname())
            except:
                address = ""
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

    def listen_client(self):
        """
            Server function.
            Used to listen incoming message from a client.
            Start a connection and :
            * if current socket corresponding to the serversocket attribute :

                * Read received command
                * Send the 'Update_Status' thread command if needed (log is not valid)

            * Else, in case of :

                * data received from client : process it reading commands from sock. Process the command or quit if asked.
                * client disconnected : remove from socket list


            See Also
            --------
            find_socket_type_within_connected_clients, set_connected_clients_table, daq_utils.ThreadCommand, read_commands, process_cmds, utility_classes.DAQ_Viewer_base.emit_status
        """
        try:
            self.processing = True
            # QtWidgets.QApplication.processEvents() #to let external commands in
            read_sockets, write_sockets, error_sockets = select.select(
                [client['socket'] for client in self.connected_clients], [],
                [client['socket'] for client in self.connected_clients],
                0)
            for sock in error_sockets:
                sock_type = self.find_socket_type_within_connected_clients(sock)
                if sock_type is not None:
                    self.connected_clients.remove(dict(socket=sock, type=sock_type))
                    self.settings.child(('conn_clients')).setValue(self.set_connected_clients_table())
                    try:
                        sock.close()
                    except:
                        pass
                    self.emit_status(ThreadCommand("Update_Status", ['Client ' + sock_type + ' disconnected', 'log']))

            for sock in read_sockets:
                QThread.msleep(100)
                # New connection
                if sock == self.serversocket:
                    (client_socket, address) = self.serversocket.accept()
                    # client_socket.setblocking(False)
                    DAQ_type = self.read_commands(client_socket)
                    if DAQ_type not in self.socket_types:
                        self.emit_status(ThreadCommand("Update_Status", [DAQ_type + ' is not a valid type', 'log']))
                        break

                    self.connected_clients.append(dict(socket=client_socket, type=DAQ_type))
                    self.settings.child(('conn_clients')).setValue(self.set_connected_clients_table())
                    self.emit_status(ThreadCommand("Update_Status",
                                                   [DAQ_type + ' connected with ' + address[0] + ':' + str(address[1]),
                                                    'log']))
                    QtWidgets.QApplication.processEvents()
                # Some incoming message from a client
                else:
                    # Data received from client, process it
                    try:
                        message = self.read_commands(sock)
                        if message == 'Done' or message == 'Info' or message == 'Infos' or message == 'Info_xml' or message == 'position_is' or message == 'move_done':
                            self.process_cmds(message)
                        elif message == 'Quit':
                            raise Exception("socket disconnect by user")
                        else:
                            self.process_cmds(message, command_sock=sock)

                    # client disconnected, so remove from socket list
                    except Exception as e:
                        sock_type = self.find_socket_type_within_connected_clients(sock)
                        if sock_type is not None:
                            self.connected_clients.remove(dict(socket=sock, type=sock_type))
                            self.settings.child(('conn_clients')).setValue(self.set_connected_clients_table())
                            # sock.shutdown(socket.SHUT_RDWR)
                            sock.close()
                            self.emit_status(
                                ThreadCommand("Update_Status", ['Client ' + sock_type + ' disconnected', 'log']))

            self.processing = False

        except Exception as e:
            self.emit_status(ThreadCommand("Update_Status", [str(e), 'log']))

    def read_commands(self, sock):
        """
            Read the commands from the given socket.

            =============== ============
            **Parameters**    **Type**
            *sock*
            =============== ============

            Returns
            -------
            message_bytes
                The readed and decoded message

            See Also
            --------
            check_received_length
        """
        message = get_string(sock)
        return message

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
                ThreadCommand("Update_Status", ['Command: ' + str(command) + ' not in the specified list', 'log']))
            return

        if sock is not None:
            send_string(sock, command)

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

            Depending on the command name :
            * Done :

                * Find a socket from the 'GRABBER' connected client.
                * Send data to a viewer or a client (depending on command_sock).

            * Info : Find a socket from the 'GRABBER' connected client and read infos.

            * Send Data 0D :

                * Find a socket from the 'GRABBER' connected client.
                * set a 1D Mock data.

            * Send Data 1D :

                * Find a socket from the 'GRABBER' connected client.
                * set a 1D Mock data.

            * Send Data 2D :

                * Find a socket from the 'GRABBER' connected client.
                * set a 2D Mock data.

            =============== =========== ==========================
            **Parameters**    **Type**    **Description**
            *command*         string      the command as a string
            *command_sock*    ???
            =============== =========== ==========================

            See Also
            --------
            find_socket_within_connected_clients, read_data, send_data, utility_classes.DAQ_Viewer_base.emit_status, daq_utils.ThreadCommand, send_command, set_1D_Mock_data, set_2D_Mock_data, process_cmds
        """
        if command not in self.message_list:
            return

        if command == 'Done':  # means the given socket finished grabbing data and is ready to send them
            self.command_done(command_sock)


        elif command == "Infos":
            try:
                sock = self.find_socket_within_connected_clients(self.client_type)
                if sock is not None:  # if client self.client_type is connected then send it the command
                    self.read_infos(sock)


            except Exception as e:
                self.emit_status(ThreadCommand("Update_Status", [str(e), 'log']))

        elif command == "Info":
            try:
                sock = self.find_socket_within_connected_clients(self.client_type)
                if sock is not None:  # if client self.client_type is connected then send it the command
                    self.read_info(sock)
            except Exception as e:
                self.emit_status(ThreadCommand("Update_Status", [str(e), 'log']))

        elif command == 'Info_xml':
            sock = self.find_socket_within_connected_clients(self.client_type)
            if sock is not None:
                list_len = get_int(sock)
                path = []
                for ind in range(list_len):
                    data_len = int.from_bytes(check_received_length(sock, 4), 'big')
                    path.append(check_received_length(sock, data_len).decode())
                data_len = int.from_bytes(check_received_length(sock, 4), 'big')
                param_xml = check_received_length(sock, data_len).decode()
                param_dict = custom_tree.XML_string_to_parameter(param_xml)[0]

                param_here = self.settings.child('infos', *path[1:])
                param_here.restoreState(param_dict)

        else:
            self.command_to_from_client(command)



    def read_infos(self, sock):
        length_bytes = check_received_length(sock, 4)
        length = np.frombuffer(length_bytes, dtype='>i4')[0]  # big endian 4 bytes==uint32 swaped
        infos = check_received_length(sock, length).decode()
        params = custom_tree.XML_string_to_parameter(infos)
        param_state = {'title': 'Infos Client:', 'name': 'infos', 'type': 'group', 'children': params}
        self.settings.child(('infos')).restoreState(param_state)

    def read_info(self, sock, dtype=np.float64):
        """
        """
        try:

            ##first get the info type
            length_bytes = check_received_length(sock, 4)
            length = np.frombuffer(length_bytes, dtype='>i4')[0]  # big endian 4 bytes==uint32 swaped
            message = check_received_length(sock, length).decode()

            # get data length
            length_bytes = check_received_length(sock, 4)
            length = np.frombuffer(length_bytes, dtype='>i4')[0]

            ##then get data
            data_bytes = check_received_length(sock, length)

            data = np.frombuffer(data_bytes, dtype=dtype)
            data = data.newbyteorder()[0]  # convert it to big endian
            try:
                self.settings.child('infos', message).setValue(data)
            except Exception as e:
                self.emit_status(ThreadCommand('Update_Status', [str(e), 'log']))

        except Exception as e:
            data = 0

        return data

if __name__ ==  '__main__':
    tcp_client = TCPClient()
    tcp_client.init_connection()
