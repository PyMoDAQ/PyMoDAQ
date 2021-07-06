import pytest
import numpy as np
import socket
import socket as native_socket

from unittest import mock
from pymodaq.daq_utils.parameter import ioxml
from pymodaq.daq_utils.parameter import utils as putils
from pymodaq.daq_utils import daq_utils as utils
from PyQt5.QtCore import pyqtSignal, QObject
from pymodaq.daq_utils.tcp_server_client import MockServer, TCPClient, Socket

from pyqtgraph.parametertree import Parameter

from time import sleep
from collections import OrderedDict

if version_mod.parse(python_version) >= version_mod.parse('3.8'):  # from version 3.8 this feature is included in the
    type_int = b'<i4'
else:
    type_int = b'<i8'


class MockPythonSocket:
    def __init__(self):
        self._send = []
        self._sendall = []
        self._recv = []
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

    def connect(self):
        pass

    def send(self, *args, **kwargs):
        self._send.append(args[0])
        return len(str(self._send[-1]))

    def sendall(self, *args, **kwargs):
        self._sendall.append(args[0])

    def recv(self, *args, **kwargs):
        if len(self._send) > 0:
            self._recv.append(self._send.pop(0))
            return self._recv.pop(0)

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
        test_Socket.send_scalar(7)
        assert test_Socket.recv() == b'\x00\x00\x00\x03'
        assert test_Socket.recv() == type_int
        assert test_Socket.recv() == b'\x00\x00\x00\x04'
        assert test_Socket.recv() == b'\x07\x00\x00\x00'

        with pytest.raises(TypeError):
            test_Socket.send_scalar('5')

    def test_get_scalar(self):
        test_Socket = Socket(MockPythonSocket())
        test_Socket.send_scalar(7.5)
        assert test_Socket.get_scalar() == 7.5

    def test_send_array(self):
        test_Socket = Socket(MockPythonSocket())
        array = np.array([1, 2, 3])
        test_Socket.send_array(array)
        assert test_Socket.recv() == b'\x00\x00\x00\x03'
        assert test_Socket.recv() == type_int
        assert test_Socket.recv() == b'\x00\x00\x00\x0c'
        assert test_Socket.recv() == b'\x00\x00\x00\x01'
        assert test_Socket.recv() == b'\x00\x00\x00\x03'
        assert test_Socket.recv() == b'\x01\x00\x00\x00\x02\x00\x00\x00\x03\x00\x00\x00'

        array = np.array([[1, 2], [2, 3]])
        test_Socket.send_array(array)
        assert test_Socket.recv() == b'\x00\x00\x00\x03'
        assert test_Socket.recv() == type_int
        assert test_Socket.recv() == b'\x00\x00\x00\x10'
        assert test_Socket.recv() == b'\x00\x00\x00\x02'
        assert test_Socket.recv() == b'\x00\x00\x00\x02'
        assert test_Socket.recv() == b'\x00\x00\x00\x02'
        assert test_Socket.recv() == b'\x01\x00\x00\x00\x02\x00\x00\x00\x02\x00\x00\x00\x03\x00\x00\x00'

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

        params_state = Parameter(name='test')
        test_TCP_Client = TCPClient(params_state=params_state)

    def test_socket(self):
        test_TCP_Client = TCPClient()
        assert test_TCP_Client.socket == None

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
