# -*- coding: utf-8 -*-
"""
Created the 26/10/2023

@author: Sebastien Weber
"""
import socket
from typing import Union


class Socket:
    """Custom Socket wrapping the built-in one and added functionalities to
    make sure message have been sent and received entirely"""
    def __init__(self, socket: socket.socket = None):
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

    def check_sended(self, data_bytes: bytes):
        """
        Make sure all bytes are sent through the socket
        Parameters
        ----------
        data_bytes: bytes
        """
        if not isinstance(data_bytes, bytes):
            raise TypeError(f'{data_bytes} should be an bytes string, not a {type(data_bytes)}')
        sended = 0
        while sended < len(data_bytes):
            sended += self.socket.send(data_bytes[sended:])

    def check_received_length(self, length) -> bytes:
        """
        Make sure all bytes (length) that should be received are received through the socket

        Parameters
        ----------
        length: int
            The number of bytes to be read from the socket

        Returns
        -------
        bytes
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

    def get_first_nbytes(self, length: int) -> bytes:
        """ Read the first N bytes from the socket

        Parameters
        ----------
        length: int
            The number of bytes to be read from the socket

        Returns
        -------
        bytes: the read bytes string
        """
        return self.check_received_length(length)

