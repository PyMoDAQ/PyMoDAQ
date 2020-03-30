import pytest
import numpy as np
import socket as native_socket
from pymodaq.daq_utils import daq_utils as utils
from PyQt5.QtCore import QThread, pyqtSignal, QObject
from pymodaq.daq_utils.tcpip_utils import Socket
from pymodaq.daq_utils.tcp_server_client import MockServer, TCPServer, TCPClient

from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import pymodaq.daq_utils.custom_parameter_tree as custom_tree

from gevent import server, socket
from time import sleep
from collections import OrderedDict

class SimpleServer(server.StreamServer):
    def __init__(self, *args, handle_fun=lambda x: print('nothing as an handle'), **kwargs):
        super().__init__(*args, **kwargs)
        self.handle_fun = handle_fun

    def handle(self, sock, address):
        self.handle_fun(sock)

### exemple of use of SimpleServer

# class Test:
#     """check the test server is working"""
#     def test(self):
#         server = SimpleServer(('127.0.0.1', 0), )
#         server.start()
#         client = Socket(socket.create_connection(('127.0.0.1', server.server_port)))
#         sleep(1)
#         server_socket = Socket(server.do_read()[0])
#
#         server_socket.sendall(b'hello and goodbye!')
#
#         response = client.recv(4096)
#         assert response == b'hello and goodbye!'
#         server.stop()



## will be used to test any kind of server derived from TCPServer
servers = [MockServer, ]

@pytest.fixture(params=servers)
def get_server(request):
    return request.param

socket_types = ["GRABBER", "ACTUATOR"]

class TestMockServer:
    """
    Test base functionnalities of the TCPServer with a small wrapper (MockServer) to init some necessary attributes
    """
    def test_attributes(self, get_server, qtbot):
        server = get_server()
        assert hasattr(server, 'emit_status')
        assert hasattr(server, 'settings')
        assert hasattr(server, 'serversocket')

        server.settings.child(('socket_ip')).setValue('999.0.0.1')  # a wrong host
        with pytest.raises(ConnectionError):
            server.init_server()

        server.close_server()

    def test_ip(self, get_server, qtbot):
        server = get_server()
        server.settings.child(('socket_ip')).setValue('999.0.0.1')  # a wrong host
        with pytest.raises(ConnectionError):
            server.init_server()
        server.close_server()

    def test_init_server(self, get_server, qtbot):
        server = get_server()
        server.settings.child(('socket_ip')).setValue('127.0.0.1')  # local host
        server.settings.child(('port_id')).setValue(6341)
        server.init_server()

        assert isinstance(server.serversocket, Socket)
        assert len(server.connected_clients) == 1
        assert server.connected_clients[0]['type'] == 'server'
        assert server.connected_clients[0]['socket'] == server.serversocket
        assert server.settings.child(('conn_clients')).value()['server'] == str(server.serversocket.getsockname())
        server.close_server()

    def test_methods(self, get_server, qtbot):
        server = get_server()
        server.settings.child(('socket_ip')).setValue('127.0.0.1')  # local host
        server.settings.child(('port_id')).setValue(6341)
        server.connected_clients.append(dict(type='server',
                                             socket=server.serversocket))
        actu_socket = Socket(native_socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        server.connected_clients.append(dict(type='ACTUATOR',
                                             socket=actu_socket))

        #find_socket_within_connected_clients
        assert server.find_socket_within_connected_clients('ACTUATOR') == actu_socket
        assert server.find_socket_within_connected_clients('ACTUAT') is None

        #find_socket_type_within_connected_clients
        assert server.find_socket_type_within_connected_clients(server.serversocket) == 'server'

        #set_connected_clients_table
        assert server.set_connected_clients_table() == OrderedDict(server="unconnected invalid socket",
                                                                   ACTUATOR="unconnected invalid socket")

        #remove_client
        server.remove_client(actu_socket)
        assert server.set_connected_clients_table() == OrderedDict(server="unconnected invalid socket")

    def test_commands(self, get_server, qtbot):
        server = get_server()
        server.socket_types = socket_types
        #Combination of general messages and specific ones (depending the connected client, Grabber or Actuator
        server.message_list = ["Quit", "Done", "Info", "Infos", "Info_xml",
                               #"Send Data 0D", "Send Data 1D", "Send Data 2D", "Send Data ND", "Status",
                               # 'x_axis', 'y_axis'
                               ]

        #read_info
        server.read_info(None, 'random_info', 'random info value')

        assert 'random_info' in custom_tree.iter_children(server.settings.child(('infos')), [])
        assert server.settings.child('infos', 'random_info').value() == 'random info value'

        # read_infos
        params = [{'title': 'Device index:', 'name': 'device', 'type': 'int', 'value': 0, 'max': 3, 'min': 0},
                    {'title': 'Infos:', 'name': 'infos', 'type': 'str', 'value': "one_info", 'readonly': True},
                    {'title': 'Line Settings:', 'name': 'line_settings', 'type': 'group', 'expanded': False,
                            'children': [
                                {'title': 'Device index:', 'name': 'device1', 'type': 'int', 'value': 0, 'max': 3,
                                 'min': 0},
                                {'title': 'Device index:', 'name': 'device2', 'type': 'int', 'value': 0, 'max': 3,
                                 'min': 0},]
                         }]

        param = Parameter.create(name='settings', type='group', children=params)
        params_xml = custom_tree.parameter_to_xml_string(param)
        server.read_infos(None, params_xml)

        assert 'device' in custom_tree.iter_children(server.settings.child(('settings_client')), [])
        assert 'infos' in custom_tree.iter_children(server.settings.child(('settings_client')), [])
        assert server.settings.child('settings_client', 'infos').value() == 'one_info'
        assert 'line_settings' in custom_tree.iter_children(server.settings.child(('settings_client')), [])
        assert server.settings.child('settings_client', 'line_settings').opts['type'] == 'group'


        # read_info_xml
        one_param = param.child(('infos'))
        one_param.setValue('another_info')
        assert one_param.value() == 'another_info'
        path = param.childPath(one_param)
        path.insert(0, '') #add one to mimic correct behaviour
        server.read_info_xml(None, path, custom_tree.parameter_to_xml_string(one_param))
        assert server.settings.child('settings_client', 'infos').value() == 'another_info'

    #

class ClientObjectManager(QObject):
    cmd_signal = pyqtSignal(utils.ThreadCommand)

class TestMockClient:
    command = ''
    commands = []
    attributes = []

    def get_cmd_signal(self, command=utils.ThreadCommand()):
        self.command = command.command
        self.commands.append(self.command)
        self.attributes = command.attributes

    def test_methods(self, qtbot):
        server = SimpleServer(('127.0.0.1', 6341), )
        server.start()


        params = [{'title': 'Device index:', 'name': 'device', 'type': 'int', 'value': 0, 'max': 3, 'min': 0},
                  {'title': 'Infos:', 'name': 'infos', 'type': 'str', 'value': "one_info", 'readonly': True},
                  {'title': 'Line Settings:', 'name': 'line_settings', 'type': 'group', 'expanded': False,
                   'children': [
                       {'name': 'someparam', 'type': 'float', 'value': 15.54, 'readonly': True},
                        ]
                   }]
        param = Parameter.create(name='settings', type='group', children=params)
        client = TCPClient(ipaddress="127.0.0.1", port=6341, params_state=param.saveState(), client_type="sometype")
        client.cmd_signal.connect(self.get_cmd_signal)

        #check init method
        assert client.ipaddress == "127.0.0.1"
        assert client.port == 6341
        assert client.client_type == 'sometype'

        client.socket = Socket(native_socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        client.socket.connect((client.ipaddress, client.port))
        sleep(0.5)
        server_socket = Socket(server.do_read()[0])


        client.send_data([np.array([0, 1, 2, 3]), 'item', 5.1])
        assert server_socket.get_string() == 'Done'
        utils.check_vals_in_iterable(server_socket.get_list(), [np.array([0, 1, 2, 3]), 'item', 5.1])

        client.send_infos_xml(custom_tree.parameter_to_xml_string(param))
        assert server_socket.get_string() == 'Infos'
        assert server_socket.get_string() == custom_tree.parameter_to_xml_string(param).decode()

        client.send_info_string('someinfo', 'this is an info')
        assert server_socket.get_string() == 'Info'
        assert server_socket.get_string() == 'someinfo'
        assert server_socket.get_string() == 'this is an info'


        #test queue_command
        client.cmd_signal.connect(self.get_cmd_signal)
        client_manager = ClientObjectManager()
        client_manager.cmd_signal.connect(client.queue_command)

        with pytest.raises(Exception):
            client.queue_command(utils.ThreadCommand('Weird command'))

        #test get_data
        server_socket.send_string('set_info')
        server_socket.send_list(['line_settings', 'someparam'])
        server_socket.send_string(custom_tree.parameter_to_xml_string(param.child('line_settings', 'someparam')))

        msg = client.socket.get_string()
        client.get_data(msg)
        assert self.command == 'set_info'
        utils.check_vals_in_iterable(self.attributes, [['line_settings', 'someparam'],
                        custom_tree.parameter_to_xml_string(param.child('line_settings', 'someparam')).decode()])


        server_socket.send_string('move_abs')
        server_socket.send_scalar(12.546)

        msg = client.socket.get_string()
        client.get_data(msg)
        assert self.command == 'move_abs'
        utils.check_vals_in_iterable(self.attributes, [12.546])

        server_socket.send_string('move_rel')
        server_socket.send_scalar(3.2)

        msg = client.socket.get_string()
        client.get_data(msg)
        assert self.command == 'move_rel'
        utils.check_vals_in_iterable(self.attributes, [3.2])

        server.stop()