import socket

import pytest

from pymodaq_utils.serialize.mysocket import Socket


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
