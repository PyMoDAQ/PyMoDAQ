import pytest
import numpy as np
import socket

from unittest import mock
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.tcp_server_client import MockServer, TCPClient, TCPServer, Socket
from pyqtgraph.parametertree import Parameter
from pyqtgraph import SRTTransform
from collections import OrderedDict
from pymodaq.utils.exceptions import ExpectedError, Expected_1, Expected_2, Expected_3
from pymodaq.utils.data import DataActuator

class MockPythonSocket:  # pragma: no cover
    def __init__(self):
        self._send = []
        self._sendall = []
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
        self._send.append(args[0])
        return len(str(self._send[-1]))

    def sendall(self, *args, **kwargs):
        self._sendall.append(args[0])

    def recv(self, *args, **kwargs):
        if len(self._send) > 0:
            return self._send.pop(0)

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
        with pytest.raises(TypeError):
            Socket.int_to_bytes('5')
            
    def test_bytes_to_int(self):
        integer = 5
        bytes_integer = Socket.int_to_bytes(integer)
        result = Socket.bytes_to_int(bytes_integer)
        assert isinstance(result, int)
        assert result == integer
        
        with pytest.raises(TypeError):
            Socket.bytes_to_int(integer)

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

        with pytest.raises(TypeError):
            test_Socket.check_received_length(100)
        
        test_Socket.send(b'test')
        with pytest.raises(TypeError):
            test_Socket.check_received_length(1.5)

    def test_send_string(self):
        test_Socket = Socket(MockPythonSocket())
        test_Socket.send_string('test')
        assert b'test' in test_Socket.socket._send
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
        assert not test_Socket.socket._send

        with pytest.raises(TypeError):
            test_Socket.send_scalar('5')

    def test_get_scalar(self):
        test_Socket = Socket(MockPythonSocket())
        test_Socket.send_scalar(7.5)
        assert test_Socket.get_scalar() == 7.5
        assert not test_Socket.socket._send

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
        assert not test_Socket.socket._send

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
        assert not test_Socket.socket._send

        with pytest.raises(TypeError):
            test_Socket.send_array(10)

    def test_get_array(self):
        test_Socket = Socket(MockPythonSocket())
        array = np.array([1, 2.1, 3.0])
        test_Socket.send_array(array)
        result = test_Socket.get_array()
        assert np.array_equal(array, result)
        assert not test_Socket.socket._send

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
        result = test_Socket.get_list()
        for elem1, elem2 in zip(data_list, result):
            if isinstance(elem1, np.ndarray):
                assert np.array_equal(elem1, elem2)
            else:
                assert elem1 == elem2
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
        data_list = [14, 1.1, 'test', np.array([1, 2, 3])]
        test_TCP_Client.send_data(data_list)
        assert test_TCP_Client.socket.get_string() == 'Done'
        result = test_TCP_Client.socket.get_list()
        for elem1, elem2 in zip(data_list, result):
            if isinstance(elem1, np.ndarray):
                assert np.array_equal(elem1, elem2)
            else:
                assert elem1 == elem2
        assert not test_TCP_Client.socket.socket._send

        with pytest.raises(TypeError):
            test_TCP_Client.send_data([1j])
        # with pytest.raises(TypeError):
        #     test_TCP_Client.send_data(10)

    def test_send_infos_xml(self):
        test_TCP_Client = TCPClient()
        test_TCP_Client.socket = Socket(MockPythonSocket())
        test_TCP_Client.send_infos_xml('test_send_infos_xml')
        assert test_TCP_Client.socket.get_string() == 'Infos'
        assert test_TCP_Client.socket.get_string() == 'test_send_infos_xml'
        assert not test_TCP_Client.socket.socket._send

    def test_send_infos_string(self):
        test_TCP_Client = TCPClient()
        test_TCP_Client.socket = Socket(MockPythonSocket())
        info_to_display = 'info to display'
        value_as_string = 192.7654
        test_TCP_Client.send_info_string(info_to_display, value_as_string)
        assert test_TCP_Client.socket.get_string() == 'Info'
        assert test_TCP_Client.socket.get_string() == info_to_display
        assert test_TCP_Client.socket.get_string() == str(value_as_string)
        assert not test_TCP_Client.socket.socket._send

    @mock.patch('pymodaq.utils.tcp_server_client.TCPClient.init_connection')
    def test_queue_command(self, mock_connection):
        mock_connection.side_effect = [Expected_1]
        command = ThreadCommand('')
        command.attribute = {'ipaddress': '0.0.0.0', 'port': 5544, 'path': [1, 2, 3],
                              'param': Parameter(name='test_param')}


        test_TCP_Client = TCPClient()
        test_TCP_Client.socket = Socket(MockPythonSocket())
        command.command = 'ini_connection'
        with pytest.raises(Expected_1):
            test_TCP_Client.queue_command(command)


        test_TCP_Client = TCPClient()
        cmd_signal = mock.Mock()
        cmd_signal.emit.side_effect = [Expected_2, Expected_3]
        test_TCP_Client.cmd_signal = cmd_signal
        command.command = 'quit'
        with pytest.raises(Expected_2):
            test_TCP_Client.queue_command(command)

        test_TCP_Client.socket = Socket(MockPythonSocket())
        with pytest.raises(Expected_3):
            test_TCP_Client.queue_command(command)
        assert test_TCP_Client.socket.socket._closed

        test_TCP_Client.socket = Socket(MockPythonSocket())
        command.command = 'update_connection'
        test_TCP_Client.queue_command(command)
        assert test_TCP_Client.ipaddress == command.attribute['ipaddress']
        assert test_TCP_Client.port == command.attribute['port']

        command.command = 'send_info'
        test_TCP_Client.queue_command(command)
        assert test_TCP_Client.socket.get_string() == 'Info_xml'
        assert test_TCP_Client.socket.get_list() == command.attribute['path']
        assert test_TCP_Client.socket.get_string()

        command.attribute = [{'data': [1, 1.1, 5]}]
        command.command = 'data_ready'
        test_TCP_Client.queue_command(command)
        assert test_TCP_Client.socket.get_string() == 'Done'
        assert test_TCP_Client.socket.get_list() == command.attribute[0]['data']

        command.attribute = [DataActuator(data=10)]
        command.command = 'position_is'
        test_TCP_Client.queue_command(command)
        assert test_TCP_Client.socket.get_string() == 'position_is'
        assert test_TCP_Client.socket.get_scalar() == command.attribute[0]

        command.command = 'move_done'
        test_TCP_Client.queue_command(command)
        assert test_TCP_Client.socket.get_string() == 'move_done'
        assert test_TCP_Client.socket.get_scalar() == command.attribute[0]

        command.attribute = [np.array([1, 2, 3])]
        command.command = 'x_axis'
        test_TCP_Client.queue_command(command)
        assert test_TCP_Client.socket.get_string() == 'x_axis'
        array = command.attribute[0]
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
        command.attribute = [{'data': np.array([1, 2, 3]), 'label': 'test', 'units': 'cm'}]
        test_TCP_Client.queue_command(command)
        assert test_TCP_Client.socket.get_string() == 'x_axis'
        array = command.attribute[0]['data']
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

    @mock.patch('pymodaq.utils.tcp_server_client.QtWidgets.QApplication.processEvents')
    @mock.patch('pymodaq.utils.tcp_server_client.select.select')
    @mock.patch('pymodaq.utils.tcp_server_client.Socket')
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
        test_Socket.send_string('init')
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
        test_TCP_Client.socket.send_list(data_list)
        test_TCP_Client.socket.send_string(data_param)
        test_TCP_Client.get_data('set_info')
        assert not test_TCP_Client.socket.socket._send

        test_TCP_Client.socket.send_scalar(10)
        test_TCP_Client.get_data('move_abs')
        assert not test_TCP_Client.socket.socket._send

        test_TCP_Client.socket.send_scalar(7)
        test_TCP_Client.get_data('move_rel')
        assert not test_TCP_Client.socket.socket._send

    def test_data_ready(self):
        test_TCP_Client = TCPClient()
        test_TCP_Client.socket = Socket(MockPythonSocket())
        data = [1, 5.3, 'test']
        datas = [{'data': data, 'name': 'TestData'}, {'data': None, 'name': 'FalseData'}]

        test_TCP_Client.data_ready(datas)
        assert test_TCP_Client.socket.get_string() == 'Done'
        result = np.array(test_TCP_Client.socket.get_list())
        assert np.array_equal(np.array(data), result)
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

    @mock.patch('pymodaq.utils.tcp_server_client.TCPServer.startTimer')
    @mock.patch('pymodaq.utils.tcp_server_client.socket')
    def test_init_server(self, mock_socket, mock_timer):
        mock_socket.socket.return_value = MockPythonSocket()
        mock_timer.side_effect = [Expected_1]

        test_TCP_Server = TCPServer()

        params = [{'name': 'socket_ip', 'value': '0.0.0.0'},
                  {'name': 'port_id', 'value': 4455},
                  {'name': 'conn_clients', 'value': None}]

        test_TCP_Server.settings = Parameter.create(name='Settings', type='group', children=params)

        with pytest.raises(Expected_1):
            test_TCP_Server.init_server()

    @mock.patch('pymodaq.utils.tcp_server_client.TCPServer.emit_status')
    @mock.patch('pymodaq.utils.tcp_server_client.TCPServer.select')
    def test_timerEvent(self, mock_select, mock_emit):
        mock_select.return_value = Exception
        mock_emit.side_effect = [ExpectedError]
        test_TCP_Server = TCPServer()
        with pytest.raises(ExpectedError):
            test_TCP_Server.timerEvent(None)

    def test_find_socket_within_connected_clients(self):
        test_TCP_Server = TCPServer()
        dict_list = [{'socket': 'Client_1', 'type': 'Server'},
                     {'socket': 'Client_2', 'type': 'Client'}]
        test_TCP_Server.connected_clients = dict_list

        assert test_TCP_Server.find_socket_within_connected_clients(None) is None
        assert test_TCP_Server.find_socket_within_connected_clients('Server') == 'Client_1'
        assert test_TCP_Server.find_socket_within_connected_clients('Client') == 'Client_2'

    def test_find_socket_type_within_connected_clients(self):
        test_TCP_Server = TCPServer()
        dict_list = [{'socket': 'Client_1', 'type': 'Server'},
                     {'socket': 'Client_2', 'type': 'Client'}]
        test_TCP_Server.connected_clients = dict_list

        assert test_TCP_Server.find_socket_type_within_connected_clients(None) is None
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

    @mock.patch('pymodaq.utils.tcp_server_client.print')
    def test_print_status(self, mock_print):
        mock_print.side_effect = [ExpectedError]
        test_TCP_Server = TCPServer()
        with pytest.raises(ExpectedError):
            test_TCP_Server.print_status('test')

    @mock.patch('pymodaq.utils.tcp_server_client.TCPServer.emit_status')
    def test_remove_client(self, mock_emit):
        mock_emit.side_effect = [Expected_1, Expected_2]

        test_TCP_Server = TCPServer()
        socket_1 = Socket(MockPythonSocket())
        socket_1.bind(('0.0.0.1', 4455))
        socket_2 = Socket(MockPythonSocket())
        socket_2.bind(('0.0.0.2', 4456))
        dict_list = [{'socket': socket_1, 'type': 'Server'},
                     {'socket': socket_2, 'type': 'Client'}]
        test_TCP_Server.connected_clients = dict_list

        params = [{'name': 'conn_clients', 'value': dict_list}]
        test_TCP_Server.settings = Parameter.create(name='Settings', type='group', children=params)

        with pytest.raises(Expected_1):
            test_TCP_Server.remove_client(socket_1)

        clients = test_TCP_Server.settings.child('conn_clients').value()
        assert not 'Server' in clients
        assert 'Client' in clients

        for socket_dict in test_TCP_Server.connected_clients:
            assert not 'Server' in socket_dict['type']

        socket_except = mock.Mock()
        socket_except.close.side_effect = [Exception]

        dict_list = [{'socket': socket_except, 'type': 'Exception'}]
        test_TCP_Server.connected_clients = dict_list

        with pytest.raises(Expected_2):
            test_TCP_Server.remove_client(socket_except)

    @mock.patch('pymodaq.utils.tcp_server_client.select.select')
    def test_select(self, mock_select):
        mock_select.return_value = ([1], [2], [3])
        test_TCP_Server = TCPServer()
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_mock_socket = MockPythonSocket()
        test_mock_socket.socket = test_socket
        result = np.array(test_TCP_Server.select([test_mock_socket]))
        assert np.array_equal(result, np.array([[1], [2], [3]]))

    @mock.patch('pymodaq.utils.tcp_server_client.TCPServer.select')
    def test_listen_client(self, mock_select):
        socket_1 = Socket(MockPythonSocket())
        socket_1.bind(('0.0.0.1', 4455))
        socket_2 = Socket(MockPythonSocket())
        socket_2.bind(('0.0.0.2', 4456))
        socket_3 = Socket(MockPythonSocket())
        socket_3.bind(('0.0.0.3', 4457))
        socket_4 = Socket(MockPythonSocket())
        socket_4.bind(('0.0.0.4', 4458))
        socket_5 = Socket(MockPythonSocket())
        socket_5.bind(('0.0.0.5', 4459))
        socket_6 = Socket(MockPythonSocket())
        socket_6.bind(('0.0.0.6', 4460))

        socket_1.send_string('')
        socket_2.send_string('Done')
        socket_3.send_string('Quit')
        socket_4.send_string('unknown')
        socket_5.send_string('test')
        socket_6.send_string('Server')

        mock_select.return_value = [[socket_2, socket_3, socket_4, socket_5],
                                    [],
                                    [socket_1]]

        test_TCP_Server = TCPServer()
        dict_list = [{'socket': socket_1, 'type': 'Server'},
                     {'socket': socket_2, 'type': 'Client'},
                     {'socket': socket_3, 'type': 'Quit'},
                     {'socket': socket_4, 'type': 'Unknown'},
                     {'socket': socket_5, 'type': 'test'},
                     {'socket': socket_6, 'type': 'serversocket'}]

        test_TCP_Server.connected_clients = dict_list

        params = [{'name': 'conn_clients', 'value': dict_list}]
        test_TCP_Server.settings = Parameter.create(name='Settings', type='group', children=params)

        test_TCP_Server.serversocket = socket_5
        test_TCP_Server.socket_types = []
        test_TCP_Server.message_list = ['Done']
        test_TCP_Server.listen_client()

        for socket_dict in test_TCP_Server.connected_clients:
            assert not 'Server' in socket_dict['type']
            assert not 'Quit' in socket_dict['type']

        clients = test_TCP_Server.settings.child('conn_clients').value()
        assert len(clients) == 4

        assert test_TCP_Server.serversocket.socket._closed

        mock_select.return_value = [[socket_6], [], []]

        dict_list = [{'socket': socket_2, 'type': 'Client'},
                     {'socket': socket_3, 'type': 'Quit'},
                     {'socket': socket_4, 'type': 'Unknown'},
                     {'socket': socket_5, 'type': 'test'},
                     {'socket': socket_6, 'type': 'serversocket'}]

        params = [{'name': 'conn_clients', 'value': dict_list}]
        test_TCP_Server.settings = Parameter.create(name='Settings', type='group', children=params)

        test_TCP_Server.serversocket = socket_6
        test_TCP_Server.socket_types = ['Server']
        test_TCP_Server.connected_clients = dict_list
        test_TCP_Server.listen_client()

        is_added = False
        for socket_dict in test_TCP_Server.connected_clients:
            if 'Server' in socket_dict['type']:
                is_added = True
        assert is_added

        assert len(test_TCP_Server.settings.child('conn_clients').value()) == 6

    @mock.patch('pymodaq.utils.tcp_server_client.TCPServer.emit_status')
    def test_send_command(self, mock_emit):
        mock_emit.side_effect = [Expected_1, None]

        test_TCP_Server = TCPServer()
        test_Socket = Socket(MockPythonSocket())
        test_TCP_Server.message_list = []
        with pytest.raises(Expected_1):
            test_TCP_Server.send_command(test_Socket)

        test_TCP_Server.message_list = ['move_at']
        test_TCP_Server.send_command(test_Socket)
        assert test_Socket.get_string() == 'move_at'

        assert not test_TCP_Server.send_command(test_Socket, command='test')

    @mock.patch('pymodaq.utils.tcp_server_client.print')
    def test_emit_status(self, mock_print):
        mock_print.side_effect = [Expected_1]
        test_TCP_Server = TCPServer()

        with pytest.raises(Expected_1):
            test_TCP_Server.emit_status('status')

    def test_read_data(self):
        test_TCP_Server = TCPServer()
        assert not test_TCP_Server.read_data(MockPythonSocket())

    def test_send_data(self):
        test_TCP_Server = TCPServer()
        assert not test_TCP_Server.send_data(MockPythonSocket(), [1, 2, 3])

    def test_command_done(self):
        test_TCP_Server = TCPServer()
        assert not test_TCP_Server.command_done(MockPythonSocket())

    def test_command_to_from_client(self):
        test_TCP_Server = TCPServer()
        assert not test_TCP_Server.command_to_from_client(MockPythonSocket())

    @mock.patch('pymodaq.utils.tcp_server_client.TCPServer.read_info_xml')
    @mock.patch('pymodaq.utils.tcp_server_client.TCPServer.emit_status')
    @mock.patch('pymodaq.utils.tcp_server_client.TCPServer.find_socket_within_connected_clients')
    def test_process_cmds(self, mock_find_socket, mock_emit, mock_read):
        mock_emit.side_effect = [None, Expected_1, Expected_2, Expected_3]

        test_TCP_Server = TCPServer()
        commands = ['Done', 'Infos', 'Info_xml', 'Info', 'test']
        test_TCP_Server.message_list = commands

        assert not test_TCP_Server.process_cmds('unknown')
        with pytest.raises(Expected_1):
            test_TCP_Server.process_cmds('unknown')

        assert not test_TCP_Server.process_cmds('Done')

        test_Socket = Socket(MockPythonSocket())
        test_Socket.send_string('test')
        mock_find_socket.return_value = test_Socket
        with pytest.raises(Expected_2):
            test_TCP_Server.process_cmds('Infos')

        mock_read.side_effect = [ExpectedError]
        test_Socket = Socket(MockPythonSocket())
        test_Socket.send_list([1, 2, 3])
        test_Socket.send_string('test')
        mock_find_socket.return_value = test_Socket
        with pytest.raises(ExpectedError):
            test_TCP_Server.process_cmds('Info_xml')

        test_Socket = Socket(MockPythonSocket())
        test_Socket.send_string('info')
        test_Socket.send_string('data')
        mock_find_socket.return_value = test_Socket
        with pytest.raises(Expected_3):
            test_TCP_Server.process_cmds('Info')

        assert not test_TCP_Server.process_cmds('test')

    @mock.patch('pymodaq.utils.parameter.ioxml.XML_string_to_parameter')
    def test_read_infos(self, mock_string):
        mock_string.return_value = []

        test_TCP_Server = TCPServer()

        params = [{'name': 'settings_client'}]
        test_TCP_Server.settings = Parameter.create(name='Settings', children=params)

        test_TCP_Server.read_infos()

    @mock.patch('pymodaq.utils.parameter.ioxml.XML_string_to_parameter')
    def test_read_info_xml(self, mock_string):
        mock_string.side_effect = [Exception, 'test', 'test']
        test_TCP_Server = TCPServer()
        settings = mock.Mock()
        settings.child.side_effect = [Exception, 'test']
        test_TCP_Server.settings = settings
        test_Socket = Socket(MockPythonSocket())
        test_Socket.send_list(['test'])
        test_Socket.send_string('test')

        with pytest.raises(Exception):
            test_TCP_Server.read_info_xml(test_Socket)

        test_Socket.send_list(['test'])
        test_Socket.send_string('test')
        with pytest.raises(Exception):
            test_TCP_Server.read_info_xml(test_Socket)

        param_here = mock.Mock()
        param_here.restoreState.side_effect = [ExpectedError]
        settings = mock.Mock()
        settings.child.return_value = param_here
        test_TCP_Server.settings = settings
        test_Socket.send_list(['test'])
        test_Socket.send_string('test')
        with pytest.raises(ExpectedError):
            test_TCP_Server.read_info_xml(test_Socket)

    @mock.patch('pymodaq.utils.parameter.utils.iter_children')
    def test_read_info(self, mock_iter_children):
        mock_iter_children.return_value = ['an_info']
        test_TCP_Server = TCPServer()
        settings = mock.Mock()
        child = mock.Mock()
        child.addChild.side_effect = [None, Expected_1]
        child.setValue.side_effect = [Expected_2]
        settings.child.return_value = child
        test_TCP_Server.settings = settings

        test_TCP_Server.read_info(test_info='another_info')
        with pytest.raises(Expected_1):
            test_TCP_Server.read_info(test_info='another_info')

        with pytest.raises(Expected_2):
            test_TCP_Server.read_info()


class TestMockServer:
    def test_init(self):
        test_MockServer = MockServer()
        assert isinstance(test_MockServer, MockServer)
