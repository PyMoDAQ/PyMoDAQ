from typing import Any, Union, TYPE_CHECKING

from pymodaq_utils.mysocket import Socket
from . import utils
from .factory import SerializableFactory, SERIALIZABLE

ser_factory = SerializableFactory()


class SocketString:
    """Mimic the Socket object but actually using a bytes string not a socket connection

    Implements a minimal interface of two methods

    Parameters
    ----------
    bytes_string: bytes

    See Also
    --------
    :class:`~pymodaq.utils.tcp_ip.mysocket.Socket`
    """
    def __init__(self, bytes_string: bytes):
        self._bytes_string = bytes_string

    def to_bytes(self):
        return self._bytes_string

    def check_received_length(self, length: int) -> bytes:
        """
        Make sure all bytes (length) that should be received are received through the socket.

        Here just read the content of the underlying bytes string

        Parameters
        ----------
        length: int
            The number of bytes to be read from the socket

        Returns
        -------
        bytes
        """
        data = self._bytes_string[0:length]
        self._bytes_string = self._bytes_string[length:]
        return data

    def get_first_nbytes(self, length: int) -> bytes:
        """ Read the first N bytes from the socket

        Parameters
        ----------
        length: int
            The number of bytes to be read from the socket

        Returns
        -------
        bytes
            the read bytes string
        """
        return self.check_received_length(length)


class Socket(Socket):
    """Custom Socket wrapping the built-in one and added functionalities to
    make sure message have been sent and received entirely"""

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

    def check_sended_with_serializer(self, obj: SERIALIZABLE):
        """ Convenience function to convert permitted objects to bytes and then use
        the check_sended method

        Appends to bytes the length of the message to make sure the reception knows how much bytes
        to expect

        For a list of allowed objects, see :meth:`Serializer.to_bytes`
        """
        # do not use Serializer anymore but mimic its behavior
        self.check_sended(ser_factory.get_apply_serializer(obj, append_length=True))

    def check_receiving(self, bytes_str: bytes):
        """ First read the 4th first bytes to get the total message length
        Make sure to read that much bytes before processing the message

        See check_sended and check_sended_with_serializer for a symmetric action
        """
        
        bytes_len_bytes, remaining_bytes = utils.split_nbytes(bytes_str, 4)
        bytes_len = utils.bytes_to_int(bytes_len_bytes)
        self.check_received_length(bytes_len)