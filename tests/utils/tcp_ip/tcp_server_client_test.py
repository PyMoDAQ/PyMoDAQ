import pytest
import numpy as np
import socket

from unittest import mock
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.tcp_ip.tcp_server_client import MockServer, TCPClient, TCPServer
from pymodaq.utils.tcp_ip.mysocket import Socket
from pymodaq.utils.tcp_ip.serializer import Serializer, DeSerializer
from pyqtgraph.parametertree import Parameter
from pyqtgraph import SRTTransform
from collections import OrderedDict
from pymodaq.utils.exceptions import ExpectedError, Expected_1, Expected_2, Expected_3
from pymodaq.utils.data import DataActuator, DataToExport


class MockPythonSocket:  # pragma: no cover
    def __init__(self):
        self._send = b''
        self._sendall = b''
        self._recv = []
        self._socket = None
        self._isconnected = False
        self._listen = False
        self.AF_INET = None
        self.SOCK_STREAM = None
        self._closed = False
        self._fileno = 1

    def bind(self, *args, **kwargs):
        arg = args[0]
        if len(arg) != 2:
            raise TypeError(f'{args} must be a tuple of two elements')
        else:
            if arg[0] == '':
                self._sockname = ('0.0.0.0', arg[1])
            else:
                self._sockname = (arg[0], arg[1])

    def listen(self, *args):
        self._listen = True

    def accept(self):
        return (self, '0.0.0.0')

    def getsockname(self):
        return self._sockname

    def connect(self, *args, **kwargs):
        self._isconnected = True

    def send(self, *args, **kwargs):
        self._send += args[0]
        return len(args[0])

    def sendall(self, *args, **kwargs):
        self._sendall += args[0]

    def recv(self, length, **kwargs):
        bytes_string = self._send[0:length]
        self._send = self._send[length:]
        return bytes_string

    def close(self):
        self._closed = True

    def setsockopt(self, *args, **kwargs):
        pass


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
        assert test_Socket.socket._listen
        assert test_Socket.getsockname() == ('0.0.0.0', 5544)
        assert test_Socket.accept()[1] == '0.0.0.0'
        test_Socket.connect()
        assert test_Socket.socket._isconnected
        test_Socket.send(b'test')
        assert b'test' in test_Socket.socket._send
        test_Socket.sendall(b'test')
        assert b'test' in test_Socket.socket._sendall
        test_Socket.recv(4)
        assert b'test' not in test_Socket.socket._send
        test_Socket.close()
        assert test_Socket.socket._closed

    def test_check_sended(self):
        test_Socket = Socket(MockPythonSocket())
        test_Socket.check_sended(b'test')
        assert b'test' in test_Socket.socket._send

        with pytest.raises(TypeError):
            test_Socket.check_sended('test')

    def test_check_received_length(self):
        test_Socket = Socket(MockPythonSocket())
        test_Socket.send(b'test')
        test_Socket.check_received_length(4)
        assert not test_Socket.socket._send

        for i in range(1025):
            test_Socket.send(b'test')
        test_Socket.check_received_length(4100)
        assert not test_Socket.socket._send


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
        assert test_TCP_Client.socket is None

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

        data = DataToExport('mydata', data=[DataActuator('mock', data=[np.array([10, 20, 30])])])
        test_TCP_Client.send_data(data)
        assert DeSerializer(test_TCP_Client.socket).string_deserialization() == 'Done'
        result = DeSerializer(test_TCP_Client.socket).dte_deserialization()
        assert result[0] == data[0]
        assert not test_TCP_Client.socket.socket._send

        with pytest.raises(TypeError):
            test_TCP_Client.send_data(data[0])
        # with pytest.raises(TypeError):
        #     test_TCP_Client.send_data(10)

    def test_send_infos_xml(self):
        test_TCP_Client = TCPClient()
        test_TCP_Client.socket = Socket(MockPythonSocket())
        test_TCP_Client.send_infos_xml('test_send_infos_xml')
        assert DeSerializer(test_TCP_Client.socket).string_deserialization() == 'Infos'
        assert DeSerializer(test_TCP_Client.socket).string_deserialization() == 'test_send_infos_xml'
        assert not test_TCP_Client.socket.socket._send

    def test_send_infos_string(self):
        test_TCP_Client = TCPClient()
        test_TCP_Client.socket = Socket(MockPythonSocket())
        info_to_display = 'info to display'
        value_as_string = 192.7654
        test_TCP_Client.send_info_string(info_to_display, value_as_string)
        assert DeSerializer(test_TCP_Client.socket).string_deserialization() == 'Info'
        assert DeSerializer(test_TCP_Client.socket).string_deserialization() == info_to_display
        assert DeSerializer(test_TCP_Client.socket).string_deserialization() == str(value_as_string)
        assert not test_TCP_Client.socket.socket._send

    @mock.patch('pymodaq.utils.tcp_ip.tcp_server_client.QtWidgets.QApplication.processEvents')
    @mock.patch('pymodaq.utils.tcp_ip.tcp_server_client.select.select')
    @mock.patch('pymodaq.utils.tcp_ip.tcp_server_client.Socket')
    def test_init_connection(self, mock_Socket, mock_select, mock_events):
        mock_Socket.return_value = Socket(MockPythonSocket())
        mock_select.side_effect = [([], [], []), Exception]
        mock_events.side_effect = [TypeError]

        test_TCP_Client = TCPClient()
        cmd_signal = mock.Mock()
        cmd_signal.emit.side_effect = [None, Expected_1]
        test_TCP_Client.cmd_signal = cmd_signal
        with pytest.raises(Expected_1):
            test_TCP_Client.init_connection(extra_commands=[ThreadCommand('test', )])
        assert not test_TCP_Client.connected

        test_TCP_Client = TCPClient()
        test_Socket = Socket(MockPythonSocket())
        test_Socket.check_sended_with_serializer('init')
        mock_Socket.return_value = test_Socket
        mock_select.side_effect = [(['init'], [], ['error'])]
        test_TCP_Client.init_connection()
        assert not test_TCP_Client.connected

        mock_Socket.side_effect = [ConnectionRefusedError]
        cmd_signal = mock.Mock()
        cmd_signal.emit.side_effect = [None, Expected_2]
        test_TCP_Client.cmd_signal = cmd_signal
        with pytest.raises(Expected_2):
            test_TCP_Client.init_connection()

    def test_get_data(self):
        test_TCP_Client = TCPClient()
        test_TCP_Client.socket = Socket(MockPythonSocket())
        data_list = [1, 2, 3]
        data_param = 'test'
        test_TCP_Client.socket.check_sended_with_serializer(data_list)
        test_TCP_Client.socket.check_sended_with_serializer(data_param)
        test_TCP_Client.get_data('set_info')
        assert not test_TCP_Client.socket.socket._send

        test_TCP_Client.socket.check_sended_with_serializer(DataActuator(10))
        test_TCP_Client.get_data('move_abs')
        assert not test_TCP_Client.socket.socket._send

        test_TCP_Client.socket.check_sended_with_serializer(DataActuator(7))
        test_TCP_Client.get_data('move_rel')
        assert not test_TCP_Client.socket.socket._send


class TestTCPServer:
    def test_init(self):
        test_TCP_Server = TCPServer()
        assert isinstance(test_TCP_Server, TCPServer)
        assert test_TCP_Server.client_type == 'GRABBER'
        assert not test_TCP_Server.connected_clients

    def test_close_server(self):
        test_TCP_Server = TCPServer()

        socket_1 = Socket(MockPythonSocket())
        socket_1.bind(('0.0.0.1', 4455))
        socket_2 = Socket(MockPythonSocket())
        socket_2.bind(('0.0.0.2', 4456))
        dict_list = [{'socket': socket_1, 'type': 'server'},
                     {'socket': socket_2, 'type': 'Client'}]
        test_TCP_Server.connected_clients = dict_list

        params = [{'name': 'conn_clients', 'value': dict_list}]
        test_TCP_Server.settings = Parameter.create(name='Settings', type='group', children=params)

        test_TCP_Server.close_server()
        for socket_dict in test_TCP_Server.connected_clients:
            assert socket_dict['type'] != 'server'

        for socket in test_TCP_Server.settings.child(('conn_clients')).value():
            assert not 'server' in socket




class TestMockServer:
    def test_init(self):
        test_MockServer = MockServer()
        assert isinstance(test_MockServer, MockServer)
