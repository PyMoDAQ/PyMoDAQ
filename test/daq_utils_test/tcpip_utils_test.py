import pytest
import numpy as np

from pymodaq.daq_utils import daq_utils as utils
from pymodaq.daq_utils.tcpip_utils import Socket

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
        server = SimpleServer(('127.0.0.1', 0))
        server.start()
        client = Socket(socket.create_connection(('127.0.0.1', server.server_port)))
        response = client.recv(4096)
        assert response == b'hello and goodbye!'
        server.stop()


class TestTCPIP:

    def test_int_to_bytes(self):
        one_integer = 254
        assert Socket.int_to_bytes(one_integer) == one_integer.to_bytes(4, 'big')

    def test_message_to_bytes(self):
        string = 'this is a message'
        assert Socket.message_to_bytes(string)[0] == string.encode()
        assert Socket.message_to_bytes(string)[1] == Socket.int_to_bytes(len(string))

    def test_check_sended(self):
        string = 'this is a message of a given length'
        server = SimpleServer(('127.0.0.1', 0), handle_fun=
                              lambda x: Socket(x).check_sended(string.encode()))
        server.start()
        client = socket.create_connection(('127.0.0.1', server.server_port))
        response = client.recv(4096)
        assert response == b'this is a message of a given length'
        client.close()
        server.stop()

    def test_check_received_length(self):
        string = 'this is a message'
        server = SimpleServer(('127.0.0.1', 0), handle_fun=
                                                lambda x: Socket(x).check_sended(string.encode()))
        server.start()
        client = Socket(socket.create_connection(('127.0.0.1', server.server_port)))
        assert client.check_received_length(len(string.encode())) == string.encode()
        client.close()
        server.stop()

    def test_send_string(self):
        string = 'this is a message'
        server = SimpleServer(('127.0.0.1', 0), handle_fun=
                                                lambda x: Socket(x).send_string(string))
        server.start()
        client = Socket(socket.create_connection(('127.0.0.1', server.server_port)))
        len_string = int.from_bytes(client.check_received_length(4), 'big')
        assert len_string == len(string)
        assert client.check_received_length(len_string) == string.encode()
        client.close()
        server.stop()

    def test_get_string(self):
        string = 'this is a message'
        server = SimpleServer(('127.0.0.1', 0), handle_fun=
                                                lambda x: Socket(x).send_string(string))
        server.start()
        client = Socket(socket.create_connection(('127.0.0.1', server.server_port)))
        assert client.get_string() == string
        client.close()
        server.stop()

    def test_get_int(self):
        one_integer = 15489
        server = SimpleServer(('127.0.0.1', 0), handle_fun=
                                                lambda x: x.sendall(Socket.int_to_bytes(one_integer)))
        server.start()
        client = Socket(socket.create_connection(('127.0.0.1', server.server_port)))
        assert client.get_int() == one_integer
        client.close()
        server.stop()

    def test_send_scalar(self):
        scalars = [15489, 2.4589]

        server = SimpleServer(('127.0.0.1', 0), )
        server.start()
        client = Socket(socket.create_connection(('127.0.0.1', server.server_port)))
        sleep(0.1)
        server_socket = Socket(server.do_read()[0])

        for scalar in scalars:
            server_socket.send_scalar(scalar)
            data_type = client.get_string()
            data_len = client.get_int()
            data_bytes = client.check_received_length(data_len)
            data = np.frombuffer(data_bytes, dtype=data_type)[0]
            assert data == scalar
        client.close()
        server.stop()

    def test_get_scalar(self):
        scalars = [15489, 2.4589]
        server = SimpleServer(('127.0.0.1', 0), )
        server.start()
        client = Socket(socket.create_connection(('127.0.0.1', server.server_port)))
        sleep(0.1)
        server_socket = Socket(server.do_read()[0])

        for scalar in scalars:
            server_socket.send_scalar(scalar)
            assert client.get_scalar() == scalar
        client.close()
        server.stop()

    def test_send_array(self):
        arrays = [np.random.rand(7, 1),
                  np.random.rand(10, 2),
                  np.random.rand(10, 2, 4),
                  np.random.rand(10, 1, 3),
                  np.random.rand(10, 4, 3, 1),
                  ]
        server = SimpleServer(('127.0.0.1', 0),)
        server.start()
        client = Socket(socket.create_connection(('127.0.0.1', server.server_port)))
        sleep(0.1)
        server_socket = Socket(server.do_read()[0])
        for array in arrays:
            server_socket.send_array(array)

            data_type = client.get_string()
            data_len = client.get_int()
            shape_len = client.get_int()
            shape = []
            for ind in range(shape_len):
                shape.append(client.get_int())
            data_bytes = client.check_received_length(data_len)

            data = np.frombuffer(data_bytes, dtype=data_type)
            data = data.reshape(tuple(shape))
            assert np.all(data == array)
        client.close()
        server.stop()

    def test_get_array(self):
        arrays = [np.random.rand(7, 1),
                  np.random.rand(10, 2),
                  np.random.rand(10, 2, 4),
                  np.random.rand(10, 1, 3),
                  np.random.rand(10, 4, 3, 1),
                  ]
        server = SimpleServer(('127.0.0.1', 0),)
        server.start()
        client = Socket(socket.create_connection(('127.0.0.1', server.server_port)))
        server_socket = Socket(server.do_read()[0])
        for array in arrays:
            server_socket.send_array(array)

            data = client.get_array()
            assert np.all(data == array)
        client.close()
        server.stop()

    def test_send_list(self):
        listing = [np.random.rand(7, 2),
                    'Hello World',
                    1,
                    2.654,
                    ]

        server = SimpleServer(('127.0.0.1', 0), handle_fun=
                              lambda x: Socket(x).send_list(listing))
        server.start()
        client = Socket(socket.create_connection(('127.0.0.1', server.server_port)))

        sleep(0.1)

        data = []
        list_len = client.get_int()

        for ind in range(list_len):
            data_type = client.get_string()
            if data_type == 'scalar':
                data.append(client.get_scalar())
            elif data_type == 'string':
                data.append(client.get_string())
            elif data_type == 'array':
                data.append(client.get_array())
        utils.check_vals_in_iterable(data, listing)


        client.close()
        server.stop()

    def test_send_another_list(self):
        listing = ['another list that should raise an exception because there is a boolean that is not a valid type',
                    ['gg',],
                    ]
        server = SimpleServer(('127.0.0.1', 0), )
        server.start()
        client = Socket(socket.create_connection(('127.0.0.1', server.server_port)))
        sleep(0.1)
        server_socket = Socket(server.do_read()[0])
        with pytest.raises(TypeError):
            assert server_socket.send_list(listing)

        server.stop()

