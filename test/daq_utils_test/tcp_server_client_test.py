import pytest
import numpy as np
import socket
from pymodaq.daq_utils import daq_utils as utils
from PyQt5.QtCore import QThread
from pymodaq.daq_utils.tcpip_utils import Socket
from pymodaq.daq_utils.tcp_server_client import MockServer, TCPServer, TCPClient

from pyqtgraph.parametertree import Parameter, ParameterTree
import pyqtgraph.parametertree.parameterTypes as pTypes
import pymodaq.daq_utils.custom_parameter_tree as custom_tree

from gevent import server, socket
from time import sleep

class SimpleServer(server.StreamServer):
    def __init__(self, *args, handle_fun=lambda x: print('nothing as an handle'), **kwargs):
        super().__init__(*args, **kwargs)
        self.handle_fun = handle_fun

    def handle(self, sock, address):
        self.handle_fun(sock)

class Test:
    """check the test server is working"""
    def test(self):
        server = SimpleServer(('127.0.0.1', 0), )
        server.start()
        client = Socket(socket.create_connection(('127.0.0.1', server.server_port)))
        sleep(0.5)
        server_socket = Socket(server.do_read()[0])

        server_socket.sendall(b'hello and goodbye!')

        response = client.recv(4096)
        assert response == b'hello and goodbye!'
        server.stop()



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


    @pytest.mark.parametrize('socket_type', socket_types)
    def test_listen(self, socket_type, get_server, qtbot):
        server = get_server()
        server.socket_types = socket_types
        server.settings.child(('socket_ip')).setValue('127.0.0.1')  # local host
        server.settings.child(('port_id')).setValue(6341)
        server.init_server()
        server_thread = QThread()
        server.moveToThread(server_thread)
        server_thread.start()

        client = Socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        client.connect((server.settings.child(('socket_ip')).value(), server.settings.child(('port_id')).value()))
        #expect a valid client type:
        client.send_string(socket_type)
        QThread.msleep(500)

        assert len(server.connected_clients) == 2
        assert socket_type in [dic['type'] for dic in server.connected_clients]
        client.send_string('Quit')
        QThread.msleep(500)
        assert len(server.connected_clients) == 1

        client = Socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        client.connect((server.settings.child(('socket_ip')).value(), server.settings.child(('port_id')).value()))
        client.send_string('a type not recognized')
        QThread.msleep(500)

        assert len(server.connected_clients) == 1
        server.close_server()
        server_thread.quit()

    def test_commands(self, get_server, qtbot):
        server = get_server()
        server.socket_types = socket_types
        #Combination of general messages and specific ones (depending the connected client, Grabber or Actuator
        server.message_list = ["Quit", "Done", "Info", "Infos", "Info_xml",
                               #"Send Data 0D", "Send Data 1D", "Send Data 2D", "Send Data ND", "Status",
                               # 'x_axis', 'y_axis'
                               ]

        server.settings.child(('socket_ip')).setValue('127.0.0.1')  # local host
        server.settings.child(('port_id')).setValue(6341)
        server.init_server()
        server_thread = QThread()
        server.moveToThread(server_thread)
        server_thread.start()

        client = Socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        client.connect((server.settings.child(('socket_ip')).value(), server.settings.child(('port_id')).value()))
        #expect a valid client type:
        client.send_string("GRABBER")

        client.send_string('Info')
        client.send_string('random_info')
        client.send_string('random info value')
        QThread.msleep(500)
        assert 'random_info' in custom_tree.iter_children(server.settings.child(('infos')), [])
        assert server.settings.child('infos', 'random_info').value() == 'random info value'


        params = [{'title': 'Device index:', 'name': 'device', 'type': 'int', 'value': 0, 'max': 3, 'min': 0},
                  {'title': 'Infos:', 'name': 'infos', 'type': 'str', 'value': "one_info", 'readonly': True},
                  {'title': 'Line Settings:', 'name': 'line_settings', 'type': 'group', 'expanded': False,
                   'children': []}]
        param = Parameter.create(name='settings', type='group', children=params)
        param_xml = custom_tree.parameter_to_xml_string(param)
        client.send_string('Infos')
        client.send_string(param_xml)
        QThread.msleep(500)
        assert 'device' in custom_tree.iter_children(server.settings.child(('settings_client')), [])
        assert 'infos' in custom_tree.iter_children(server.settings.child(('settings_client')), [])
        assert server.settings.child('settings_client', 'infos').value() == 'one_info'
        assert 'line_settings' in custom_tree.iter_children(server.settings.child(('settings_client')), [])
        assert server.settings.child('settings_client', 'line_settings').opts['type'] == 'group'

        param.child(('infos')).setValue('another_info')
        client.send_string('Info_xml')
        client.send_list(custom_tree.get_param_path(param.child(('infos'))))
        client.send_string(custom_tree.parameter_to_xml_string(param.child(('infos'))))
        QThread.msleep(500)
        assert server.settings.child('settings_client', 'infos').value() == 'another_info'
        server.close_server()
        server_thread.quit()

class TestMockClient:
    command = ''
    attributes = []
    def get_cmd_signal(self, command=utils.ThreadCommand()):
        self.command = command.command
        self.attributes = command.attributes

    def test_init_connection(self, get_server, qtbot):
        server = get_server()
        server.socket_types = socket_types
        # Combination of general messages and specific ones (depending the connected client, Grabber or Actuator
        server.message_list = ["Quit", "Done", "Info", "Infos", "Info_xml",
                               # "Send Data 0D", "Send Data 1D", "Send Data 2D", "Send Data ND", "Status",
                               # 'x_axis', 'y_axis'
                               ]

        server.settings.child(('socket_ip')).setValue('127.0.0.1')  # local host
        server.settings.child(('port_id')).setValue(6341)
        server.init_server()
        server_thread = QThread()
        server.moveToThread(server_thread)
        server_thread.start()


        params = [{'title': 'Device index:', 'name': 'device', 'type': 'int', 'value': 0, 'max': 3, 'min': 0},
                  {'title': 'Infos:', 'name': 'infos', 'type': 'str', 'value': "one_info", 'readonly': True},
                  {'title': 'Line Settings:', 'name': 'line_settings', 'type': 'group', 'expanded': False,
                   'children': []}]
        param = Parameter.create(name='settings', type='group', children=params)
        client = TCPClient(ipaddress="127.0.0.1", port=6341, params_state=param.saveState(), client_type="GRABBER")
        client.cmd_signal.connect(self.get_cmd_signal)
        client.init_connection()

        assert self.command == 'connected'