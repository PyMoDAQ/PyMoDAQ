import pytest
import numpy as np
import socket
import socket as native_socket

from unittest import mock
from pymodaq.daq_utils.parameter import ioxml
from pymodaq.daq_utils.parameter import utils as putils
from pymodaq.daq_utils.daq_utils import ThreadCommand
from PyQt5.QtCore import pyqtSignal, QObject
from pymodaq.daq_utils.tcp_server_client import MockServer, TCPClient, TCPServer, Socket

from pyqtgraph.parametertree import Parameter

from time import sleep
from collections import OrderedDict
import sys
from packaging import version as version_mod


class MockPythonSocket:  # pragma: no cover
    def __init__(self):
        self._send = []
        self._sendall = []
        self._recv = []
        self._socket = None
        self.AF_INET = None
        self.SOCK_STREAM = None
        self._closed = False

    def bind(self, *args, **kwargs):
        arg = args[0]
        if len(arg) != 2:
            raise TypeError(f'{args} must be a tuple of two elements')
        else:
            if arg[0] == '':
                self._sockname = ('0.0.0.0', arg[1])
            else:
                self._sockname = (arg[0], arg[1])

    def listen(self):
        pass

    def accept(self):
        return (MockPythonSocket(), '0.0.0.0')

    def getsockname(self):
        return self._sockname

    def connect(self, *args, **kwargs):
        pass

    def send(self, *args, **kwargs):
        self._send.append(args[0])
        return len(str(self._send[-1]))

    def sendall(self, *args, **kwargs):
        self._sendall.append(args[0])

    def recv(self, *args, **kwargs):
        if len(self._send) > 0:
            return self._send.pop(0)

    def close(self):
        self._closed = True


class TestSocket:
    def test_init(self):
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_Socket = Socket(test_socket)
        assert isinstance(test_Socket, Socket)
        assert test_Socket.socket == test_socket
        assert test_Socket.__eq__(test_Socket)
    
    def test_base_fun(self):
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_Socket = Socket(test_socket)
        test_Socket.bind(('', 5544))
        test_Socket.listen
        assert test_Socket.getsockname() == ('0.0.0.0', 5544)
        assert test_Socket.accept
        assert test_Socket.connect
        assert test_Socket.send
        assert test_Socket.sendall
        assert test_Socket.recv
        test_Socket.close()

        test_socket = MockPythonSocket()
        test_Socket = Socket(test_socket)
        test_Socket.bind(('', 5544))
        test_Socket.listen()
        test_Socket.getsockname() == ('0.0.0.0', 5544)
        test_Socket.accept()
        test_Socket.connect()
        test_Socket.send(b'test')
        test_Socket.sendall(b'test')
        test_Socket.recv(4)
        test_Socket.close()
        
    def test_message_to_bytes(self):
        message = 10
        bytes_message = Socket.message_to_bytes(message)
        assert isinstance(bytes_message[0], bytes)
        assert isinstance(bytes_message[1], bytes)

    def test_int_to_bytes(self):
        integer = 5
        bytes_integer = Socket.int_to_bytes(integer)
        assert isinstance(bytes_integer, bytes)

        with pytest.raises(TypeError):
            Socket.int_to_bytes(1.5)
            
    def test_bytes_to_int(self):
        integer = 5
        bytes_integer = Socket.int_to_bytes(integer)
        integer_2 = Socket.bytes_to_int(bytes_integer)
        assert isinstance(integer_2, int)
        assert integer_2 == integer
        
        with pytest.raises(TypeError):
            Socket.bytes_to_int(integer)

    def test_check_sended(self):
        test_Socket = Socket(MockPythonSocket())
        test_Socket.check_sended(b'test')

        with pytest.raises(TypeError):
            test_Socket.check_sended('test')

    def test_check_received_length(self):
        test_Socket = Socket(MockPythonSocket())
        test_Socket.send(b'test')
        test_Socket.check_received_length(4)

        for i in range(1025):
            test_Socket.send(b'test')
        test_Socket.check_received_length(4100)

        with pytest.raises(TypeError):
            test_Socket.check_received_length(100)

        with pytest.raises(TypeError):
            test_Socket.check_received_length(1.5)

    def test_send_string(self):
        test_Socket = Socket(MockPythonSocket())
        test_Socket.send_string('test')
        assert test_Socket.recv() == b'\x00\x00\x00\x04'
        assert test_Socket.recv() == b'test'

    def test_get_string(self):
        test_Socket = Socket(MockPythonSocket())
        test_Socket.send_string('test')
        assert test_Socket.get_string() == 'test'

    def test_get_int(self):
        test_Socket = Socket(MockPythonSocket())
        test_Socket.send_string('test')
        assert test_Socket.get_int() == 4

    def test_send_scalar(self):
        test_Socket = Socket(MockPythonSocket())
        scalar = 7
        test_Socket.send_scalar(scalar)

        data = np.array(scalar)
        data_bytes = data.tobytes()
        data_type = data.dtype.descr[0][1]
        cmd_bytes, cmd_length_bytes = test_Socket.message_to_bytes(data_type)

        assert test_Socket.recv() == cmd_length_bytes
        assert test_Socket.recv() == cmd_bytes
        assert test_Socket.recv() == test_Socket.int_to_bytes(len(data_bytes))
        assert test_Socket.recv() == data_bytes
        assert not test_Socket.recv()

        with pytest.raises(TypeError):
            test_Socket.send_scalar('5')

    def test_get_scalar(self):
        test_Socket = Socket(MockPythonSocket())
        test_Socket.send_scalar(7.5)
        assert test_Socket.get_scalar() == 7.5

    def test_send_array(self):
        test_Socket = Socket(MockPythonSocket())
        data = np.array([1, 2, 3])
        test_Socket.send_array(data)

        data_bytes = data.tobytes()
        data_type = data.dtype.descr[0][1]
        cmd_bytes, cmd_length_bytes = test_Socket.message_to_bytes(data_type)

        assert test_Socket.recv() == cmd_length_bytes
        assert test_Socket.recv() == cmd_bytes
        assert test_Socket.recv() == test_Socket.int_to_bytes(len(data_bytes))
        assert test_Socket.recv() == test_Socket.int_to_bytes(len(data.shape))
        for i in range(len(data.shape)):
            assert test_Socket.recv() == test_Socket.int_to_bytes(data.shape[i])
        assert test_Socket.recv() == data_bytes
        assert not test_Socket.recv()

        data = np.array([[1, 2], [2, 3]])
        test_Socket.send_array(data)

        data_bytes = data.tobytes()
        data_type = data.dtype.descr[0][1]
        cmd_bytes, cmd_length_bytes = test_Socket.message_to_bytes(data_type)

        assert test_Socket.recv() == cmd_length_bytes
        assert test_Socket.recv() == cmd_bytes
        assert test_Socket.recv() == test_Socket.int_to_bytes(len(data_bytes))
        assert test_Socket.recv() == test_Socket.int_to_bytes(len(data.shape))
        for i in range(len(data.shape)):
            assert test_Socket.recv() == test_Socket.int_to_bytes(data.shape[i])
        assert test_Socket.recv() == data_bytes
        assert not test_Socket.recv()

        with pytest.raises(TypeError):
            test_Socket.send_array(10)

    def test_get_array(self):
        test_Socket = Socket(MockPythonSocket())
        array = np.array([1, 2.1, 3.0])
        test_Socket.send_array(array)
        result = test_Socket.get_array()
        assert np.array_equal(array, result)

    def test_send_list(self):
        test_Socket = Socket(MockPythonSocket())
        data_list = [np.array([1, 2]), 'test', 47]
        test_Socket.send_list(data_list)
        assert test_Socket.recv() == b'\x00\x00\x00\x03'
        assert test_Socket.get_string() == 'array'
        assert np.array_equal(test_Socket.get_array(), data_list[0])
        assert test_Socket.get_string() == 'string'
        assert test_Socket.get_string() == data_list[1]
        assert test_Socket.get_string() == 'scalar'
        assert test_Socket.get_scalar() == data_list[2]

        with pytest.raises(TypeError):
            test_Socket.send_list([test_Socket])

        with pytest.raises(TypeError):
            test_Socket.send_list(15)

    def test_get_list(self):
        test_Socket = Socket(MockPythonSocket())
        data_list = [np.array([1, 2]), 'test', 47]
        test_Socket.send_list(data_list)
        np_list = np.array(data_list)
        result = np.array(test_Socket.get_list())
        for elem1, elem2 in zip(np_list, result):
            if isinstance(elem1, np.ndarray):
                assert np.array_equal(elem1, elem2)
            else :
                assert elem1 == elem2


class TestTCPClient:
    def test_init(self):
        params_state = {'Name': 'test_params', 'value': None}
        test_TCP_Client = TCPClient(params_state=params_state)
        assert isinstance(test_TCP_Client, TCPClient)

        params_state = Parameter(name='test')
        test_TCP_Client = TCPClient(params_state=params_state)
        assert isinstance(test_TCP_Client, TCPClient)

    def test_socket(self):
        test_TCP_Client = TCPClient()
        assert test_TCP_Client.socket == None

        test_TCP_Client.socket = Socket(MockPythonSocket())
        assert isinstance(test_TCP_Client.socket, Socket)

    def test_close(self):
        test_TCP_Client = TCPClient()
        test_TCP_Client.socket = Socket(MockPythonSocket())
        test_TCP_Client.close()
        assert test_TCP_Client.socket.socket._closed

    def test_send_data(self):
        test_TCP_Client = TCPClient()
        test_TCP_Client.socket = Socket(MockPythonSocket())
        data_list = [14, 1.1, 'test', np.array([1, 2, 3])]
        test_TCP_Client.send_data(data_list)
        assert test_TCP_Client.socket.get_string() == 'Done'
        np_list = np.array(data_list)
        result = test_TCP_Client.socket.get_list()
        for elem1, elem2 in zip(np_list, result):
            if isinstance(elem1, np.ndarray):
                assert np.array_equal(elem1, elem2)
            else:
                assert elem1 == elem2

        with pytest.raises(TypeError):
            test_TCP_Client.send_data([1j])

    def test_send_infos_xml(self):
        test_TCP_Client = TCPClient()
        test_TCP_Client.socket = Socket(MockPythonSocket())
        test_TCP_Client.send_infos_xml('test_send_infos_xml')
        assert test_TCP_Client.socket.get_string() == 'Infos'
        assert test_TCP_Client.socket.get_string() == 'test_send_infos_xml'

    def test_send_infos_string(self):
        test_TCP_Client = TCPClient()
        test_TCP_Client.socket = Socket(MockPythonSocket())
        info_to_display = 'info to display'
        value_as_string = 192.7654
        test_TCP_Client.send_info_string(info_to_display, value_as_string)
        assert test_TCP_Client.socket.get_string() == 'Info'
        assert test_TCP_Client.socket.get_string() == info_to_display
        assert test_TCP_Client.socket.get_string() == str(value_as_string)

    def test_queue_command(self):
        test_TCP_Client = TCPClient()
        command = mock.Mock()
        command.attributes = {'ipaddress': '0.0.0.0', 'port': 5544, 'path': [1, 2, 3],
                              'param': Parameter(name='test_param')}
        command.command = 'quit'
        test_TCP_Client.queue_command(command)

        test_TCP_Client.socket = Socket(MockPythonSocket())
        test_TCP_Client.queue_command(command)
        assert test_TCP_Client.socket.socket._closed

        test_TCP_Client.socket = Socket(MockPythonSocket())
        command.command = 'update_connection'
        test_TCP_Client.queue_command(command)
        assert test_TCP_Client.ipaddress == command.attributes['ipaddress']
        assert test_TCP_Client.port == command.attributes['port']

        command.command = 'send_info'
        test_TCP_Client.queue_command(command)
        assert test_TCP_Client.socket.get_string() == 'Info_xml'
        assert test_TCP_Client.socket.get_list() == command.attributes['path']
        assert test_TCP_Client.socket.get_string()

        command.attributes = [{'data': [1, 1.1, 5]}]
        command.command = 'data_ready'
        test_TCP_Client.queue_command(command)
        assert test_TCP_Client.socket.get_string() == 'Done'
        assert test_TCP_Client.socket.get_list() == command.attributes[0]['data']

        command.attributes = [10]
        command.command = 'position_is'
        test_TCP_Client.queue_command(command)
        assert test_TCP_Client.socket.get_string() == 'position_is'
        assert test_TCP_Client.socket.get_scalar() == command.attributes[0]

        command.command = 'move_done'
        test_TCP_Client.queue_command(command)
        assert test_TCP_Client.socket.get_string() == 'move_done'
        assert test_TCP_Client.socket.get_scalar() == command.attributes[0]

        command.attributes = [np.array([1, 2, 3])]
        command.command = 'x_axis'
        test_TCP_Client.queue_command(command)
        assert test_TCP_Client.socket.get_string() == 'x_axis'
        array = command.attributes[0]
        result = test_TCP_Client.socket.get_array()
        for val1, val2 in zip(array, result):
            assert val1 == val2
        assert test_TCP_Client.socket.get_string() == ''
        assert test_TCP_Client.socket.get_string() == ''

        command.command = 'y_axis'
        test_TCP_Client.queue_command(command)
        assert test_TCP_Client.socket.get_string() == 'y_axis'
        result = test_TCP_Client.socket.get_array()
        for val1, val2 in zip(array, result):
            assert val1 == val2
        assert test_TCP_Client.socket.get_string() == ''
        assert test_TCP_Client.socket.get_string() == ''

        command.command = 'x_axis'
        command.attributes = [{'data': np.array([1, 2, 3]), 'label': 'test', 'units': 'cm'}]
        test_TCP_Client.queue_command(command)
        assert test_TCP_Client.socket.get_string() == 'x_axis'
        array = command.attributes[0]['data']
        result = test_TCP_Client.socket.get_array()
        for val1, val2 in zip(array, result):
            assert val1 == val2
        assert test_TCP_Client.socket.get_string() == 'test'
        assert test_TCP_Client.socket.get_string() == 'cm'

        command.command = 'y_axis'
        test_TCP_Client.queue_command(command)
        assert test_TCP_Client.socket.get_string() == 'y_axis'
        result = test_TCP_Client.socket.get_array()
        for val1, val2 in zip(array, result):
            assert val1 == val2
        assert test_TCP_Client.socket.get_string() == 'test'
        assert test_TCP_Client.socket.get_string() == 'cm'

        command.command = 'test'
        with pytest.raises(IOError):
            test_TCP_Client.queue_command(command)

    @mock.patch('pymodaq.daq_utils.tcp_server_client.Socket')
    def test_init_connection(self, mock_Socket):
        mock_Socket.return_value = Socket(MockPythonSocket())
        test_TCP_Client = TCPClient()
        test_TCP_Client.init_connection(extra_commands=[ThreadCommand('test')])

        command = mock.Mock()
        command.command = 'ini_connection'
        test_TCP_Client.queue_command(command)

    def test_get_data(self):
        test_TCP_Client = TCPClient()
        test_TCP_Client.socket = Socket(MockPythonSocket())
        data_list = [1, 2, 3]
        data_param = 'test'
        test_TCP_Client.socket.send_list(data_list)
        test_TCP_Client.socket.send_string(data_param)
        test_TCP_Client.get_data('set_info')

        test_TCP_Client.socket.send_scalar(10)
        test_TCP_Client.get_data('move_abs')

        test_TCP_Client.socket.send_scalar(7)
        test_TCP_Client.get_data('move_rel')


class TestTCPServer:
    def test_init(self):
        test_TCP_Server = TCPServer()
        assert isinstance(test_TCP_Server, TCPServer)

    def test_close_server(self):
        test_TCP_Server = TCPServer()
        test_TCP_Server.close_server()

    # @mock.patch('pymodaq.daq_utils.tcp_server_client.Socket')
    # def test_init_server(self, mock_Socket):
    #     mock_Socket.return_value = Socket(MockPythonSocket())
    #     test_TCP_Server = TCPServer()
    #     test_TCP_Server.init_server()

    @mock.patch('pymodaq.daq_utils.tcp_server_client.TCPServer.select')
    def test_timerEvent(self, mock_select):
        mock_select.return_value = Exception
        test_TCP_Server = TCPServer()
        test_TCP_Server.timerEvent(None)

    def test_find_socket_within_connected_clients(self):
        test_TCP_Server = TCPServer()
        dict_list = [{'socket': 'Client_1', 'type': 'Server'},
                     {'socket': 'Client_2', 'type': 'Client'}]
        test_TCP_Server.connected_clients = dict_list

        assert not test_TCP_Server.find_socket_within_connected_clients(None)
        assert test_TCP_Server.find_socket_within_connected_clients('Server') == 'Client_1'
        assert test_TCP_Server.find_socket_within_connected_clients('Client') == 'Client_2'

    def test_find_socket_type_within_connected_clients(self):
        test_TCP_Server = TCPServer()
        dict_list = [{'socket': 'Client_1', 'type': 'Server'},
                     {'socket': 'Client_2', 'type': 'Client'}]
        test_TCP_Server.connected_clients = dict_list

        assert not test_TCP_Server.find_socket_type_within_connected_clients(None)
        assert test_TCP_Server.find_socket_type_within_connected_clients('Client_1') == 'Server'
        assert test_TCP_Server.find_socket_type_within_connected_clients('Client_2') == 'Client'

    def test_set_connected_clients_table(self):
        test_TCP_Server = TCPServer()

        socket_1 = Socket(MockPythonSocket())
        socket_1.bind(('0.0.0.1', 4455))
        socket_2 = Socket(MockPythonSocket())
        socket_2.bind(('0.0.0.2', 4456))
        dict_list = [{'socket': socket_1, 'type': 'Server'},
                     {'socket': socket_2, 'type': 'Client'}]
        test_TCP_Server.connected_clients = dict_list
        result = test_TCP_Server.set_connected_clients_table()
        assert isinstance(result, OrderedDict)
        assert result['Server'] == "('0.0.0.1', 4455)"
        assert result['Client'] == "('0.0.0.2', 4456)"

        socket_except = Socket(MockPythonSocket())
        socket_except._sockname = Exception
        test_TCP_Server.connected_clients = [{'socket': socket_except, 'type': None}]
        result = test_TCP_Server.set_connected_clients_table()
        assert result[None] == 'unconnected invalid socket'

    def test_print_status(self):
        test_TCP_Server = TCPServer()
        test_TCP_Server.print_status('test')

    def test_remove_client(self):
        test_TCP_Server = TCPServer()

        socket_1 = Socket(MockPythonSocket())
        socket_1.bind(('0.0.0.1', 4455))
        socket_2 = Socket(MockPythonSocket())
        socket_2.bind(('0.0.0.2', 4456))
        dict_list = [{'socket': socket_1, 'type': 'Server'},
                     {'socket': socket_2, 'type': 'Client'}]
        test_TCP_Server.connected_clients = dict_list

        settings = mock.Mock()
        test_TCP_Server.settings = settings

        test_TCP_Server.remove_client(socket_1)

        is_removed = True
        for socket_dict in test_TCP_Server.connected_clients:
            if 'Server' in socket_dict['type']:
                is_removed = False

        assert is_removed

        socket_except = mock.Mock()
        socket_except.close.side_effect = [Exception]

        dict_list = [{'socket': socket_except, 'type': 'Exception'}]
        test_TCP_Server.connected_clients = dict_list

        test_TCP_Server.remove_client(socket_except)

    @mock.patch('pymodaq.daq_utils.tcp_server_client.TCPServer.find_socket_within_connected_clients')
    def test_process_cmds(self, mock_find_socket):
        mock_find_socket.return_value = Socket(MockPythonSocket())
        test_TCP_Server = TCPServer()
        commands = ['Done', 'Infos', 'Info_xml', 'Info', 'test']

        test_TCP_Server.message_list = commands
        assert not test_TCP_Server.process_cmds('unknown')

        assert not test_TCP_Server.process_cmds('Done')

        test_Socket = Socket(MockPythonSocket())
        test_Socket.send_string('test')
        mock_find_socket.return_value = test_Socket
        test_TCP_Server.process_cmds('Infos')

        test_Socket = Socket(MockPythonSocket())
        test_Socket.send_list([1, 2, 3])
        test_Socket.send_string('test')
        mock_find_socket.return_value = test_Socket
        with pytest.raises(Exception):
            test_TCP_Server.process_cmds('Info_xml')

        test_Socket = Socket(MockPythonSocket())
        test_Socket.send_string('info')
        test_Socket.send_string('data')
        mock_find_socket.return_value = test_Socket
        test_TCP_Server.process_cmds('Info')

        assert not test_TCP_Server.process_cmds('test')
#
# # will be used to test any kind of server derived from TCPServer
# servers = [MockServer, ]
#
#
# @pytest.fixture(params=servers)
# def get_server(request):
#     return request.param
#
#
# socket_types = ["GRABBER", "ACTUATOR"]
#
#
# class TestMockServer:
#     """
#     Test base functionnalities of the TCPServer with a small wrapper (MockServer) to init some necessary attributes
#     """
#
#     def test_attributes(self, get_server, qtbot):
#         server = get_server()
#         assert hasattr(server, 'emit_status')
#         assert hasattr(server, 'settings')
#         assert hasattr(server, 'serversocket')
#
#         server.settings.child(('socket_ip')).setValue('999.0.0.1')  # a wrong host
#         with pytest.raises(ConnectionError):
#             server.init_server()
#
#         server.close_server()
#
#     def test_ip(self, get_server, qtbot):
#         server = get_server()
#         server.settings.child(('socket_ip')).setValue('999.0.0.1')  # a wrong host
#         with pytest.raises(ConnectionError):
#             server.init_server()
#         server.close_server()
#
#     def test_init_server(self, get_server, qtbot):
#         server = get_server()
#         server.settings.child(('socket_ip')).setValue('127.0.0.1')  # local host
#         server.settings.child(('port_id')).setValue(6341)
#         server.init_server()
#
#         assert isinstance(server.serversocket, Socket)
#         assert len(server.connected_clients) == 1
#         assert server.connected_clients[0]['type'] == 'server'
#         assert server.connected_clients[0]['socket'] == server.serversocket
#         assert server.settings.child(('conn_clients')).value()['server'] == str(server.serversocket.getsockname())
#         server.close_server()
#
#     def test_methods(self, get_server, qtbot):
#         server = get_server()
#         server.settings.child(('socket_ip')).setValue('127.0.0.1')  # local host
#         server.settings.child(('port_id')).setValue(6341)
#         server.connected_clients.append(dict(type='server',
#                                              socket=server.serversocket))
#         actu_socket = Socket(native_socket.socket(socket.AF_INET, socket.SOCK_STREAM))
#         server.connected_clients.append(dict(type='ACTUATOR',
#                                              socket=actu_socket))
#
#         # find_socket_within_connected_clients
#         assert server.find_socket_within_connected_clients('ACTUATOR') == actu_socket
#         assert server.find_socket_within_connected_clients('ACTUAT') is None
#
#         # find_socket_type_within_connected_clients
#         assert server.find_socket_type_within_connected_clients(server.serversocket) == 'server'
#
#         # set_connected_clients_table
#         assert server.set_connected_clients_table() == OrderedDict(server="unconnected invalid socket",
#                                                                    ACTUATOR="unconnected invalid socket")
#
#         # remove_client
#         server.remove_client(actu_socket)
#         assert server.set_connected_clients_table() == OrderedDict(server="unconnected invalid socket")
#
#     def test_commands(self, get_server, qtbot):
#         server = get_server()
#         server.socket_types = socket_types
#         # Combination of general messages and specific ones (depending the connected client, Grabber or Actuator
#         server.message_list = ["Quit", "Done", "Info", "Infos", "Info_xml",
#                                # "Send Data 0D", "Send Data 1D", "Send Data 2D", "Send Data ND", "Status",
#                                # 'x_axis', 'y_axis'
#                                ]
#
#         # read_info
#         server.read_info(None, 'random_info', 'random info value')
#
#         assert 'random_info' in putils.iter_children(server.settings.child(('infos')), [])
#         assert server.settings.child('infos', 'random_info').value() == 'random info value'
#
#         # read_infos
#         params = [{'title': 'Device index:', 'name': 'device', 'type': 'int', 'value': 0, 'max': 3, 'min': 0},
#                   {'title': 'Infos:', 'name': 'infos', 'type': 'str', 'value': "one_info", 'readonly': True},
#                   {'title': 'Line Settings:', 'name': 'line_settings', 'type': 'group', 'expanded': False,
#                    'children': [
#                        {'title': 'Device index:', 'name': 'device1', 'type': 'int', 'value': 0, 'max': 3,
#                         'min': 0},
#                        {'title': 'Device index:', 'name': 'device2', 'type': 'int', 'value': 0, 'max': 3,
#                         'min': 0}, ]
#                    }]
#
#         param = Parameter.create(name='settings', type='group', children=params)
#         params_xml = ioxml.parameter_to_xml_string(param)
#         server.read_infos(None, params_xml)
#
#         assert 'device' in putils.iter_children(server.settings.child(('settings_client')), [])
#         assert 'infos' in putils.iter_children(server.settings.child(('settings_client')), [])
#         assert server.settings.child('settings_client', 'infos').value() == 'one_info'
#         assert 'line_settings' in putils.iter_children(server.settings.child(('settings_client')), [])
#         assert server.settings.child('settings_client', 'line_settings').opts['type'] == 'group'
#
#         # read_info_xml
#         one_param = param.child(('infos'))
#         one_param.setValue('another_info')
#         assert one_param.value() == 'another_info'
#         path = param.childPath(one_param)
#         path.insert(0, '')  # add one to mimic correct behaviour
#         server.read_info_xml(None, path, ioxml.parameter_to_xml_string(one_param))
#         assert server.settings.child('settings_client', 'infos').value() == 'another_info'
#
#     #
#
#
# class ClientObjectManager(QObject):
#     cmd_signal = pyqtSignal(utils.ThreadCommand)
#
#
# class TestMockClient:
#     command = ''
#     commands = []
#     attributes = []
#
#     def get_cmd_signal(self, command=utils.ThreadCommand()):
#         self.command = command.command
#         self.commands.append(self.command)
#         self.attributes = command.attributes
#
#     def test_methods(self, qtbot):
#         server = SimpleServer(('127.0.0.1', 6341), )
#         server.start()
#
#         params = [{'title': 'Device index:', 'name': 'device', 'type': 'int', 'value': 0, 'max': 3, 'min': 0},
#                   {'title': 'Infos:', 'name': 'infos', 'type': 'str', 'value': "one_info", 'readonly': True},
#                   {'title': 'Line Settings:', 'name': 'line_settings', 'type': 'group', 'expanded': False,
#                    'children': [
#                        {'name': 'someparam', 'type': 'float', 'value': 15.54, 'readonly': True},
#                    ]
#                    }]
#         param = Parameter.create(name='settings', type='group', children=params)
#         client = TCPClient(ipaddress="127.0.0.1", port=6341, params_state=param.saveState(), client_type="sometype")
#         client.cmd_signal.connect(self.get_cmd_signal)
#
#         # check init method
#         assert client.ipaddress == "127.0.0.1"
#         assert client.port == 6341
#         assert client.client_type == 'sometype'
#
#         client.socket = Socket(native_socket.socket(socket.AF_INET, socket.SOCK_STREAM))
#         client.socket.connect((client.ipaddress, client.port))
#         sleep(0.5)
#         server_socket = Socket(server.do_read()[0])
#
#         client.send_data([np.array([0, 1, 2, 3]), 'item', 5.1])
#         assert server_socket.get_string() == 'Done'
#         utils.check_vals_in_iterable(server_socket.get_list(), [np.array([0, 1, 2, 3]), 'item', 5.1])
#
#         client.send_infos_xml(ioxml.parameter_to_xml_string(param))
#         assert server_socket.get_string() == 'Infos'
#         assert server_socket.get_string() == ioxml.parameter_to_xml_string(param).decode()
#
#         client.send_info_string('someinfo', 'this is an info')
#         assert server_socket.get_string() == 'Info'
#         assert server_socket.get_string() == 'someinfo'
#         assert server_socket.get_string() == 'this is an info'
#
#         # test queue_command
#         client.cmd_signal.connect(self.get_cmd_signal)
#         client_manager = ClientObjectManager()
#         client_manager.cmd_signal.connect(client.queue_command)
#
#         with pytest.raises(Exception):
#             client.queue_command(utils.ThreadCommand('Weird command'))
#
#         # test get_data
#         server_socket.send_string('set_info')
#         server_socket.send_list(['line_settings', 'someparam'])
#         server_socket.send_string(ioxml.parameter_to_xml_string(param.child('line_settings', 'someparam')))
#
#         msg = client.socket.get_string()
#         client.get_data(msg)
#         assert self.command == 'set_info'
#         utils.check_vals_in_iterable(self.attributes, [['line_settings', 'someparam'],
#                                                        ioxml.parameter_to_xml_string(
#                                                            param.child('line_settings', 'someparam')).decode()])
#
#         server_socket.send_string('move_abs')
#         server_socket.send_scalar(12.546)
#
#         msg = client.socket.get_string()
#         client.get_data(msg)
#         assert self.command == 'move_abs'
#         utils.check_vals_in_iterable(self.attributes, [12.546])
#
#         server_socket.send_string('move_rel')
#         server_socket.send_scalar(3.2)
#
#         msg = client.socket.get_string()
#         client.get_data(msg)
#         assert self.command == 'move_rel'
#         utils.check_vals_in_iterable(self.attributes, [3.2])
#
#         server.stop()

class TestMockServer:
    def test_init(self):
        test_MockServer = MockServer()
