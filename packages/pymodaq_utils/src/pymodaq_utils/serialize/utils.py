import numpy as np
from typing import Tuple, Union


def split_nbytes(bytes_str: bytes, bytes_len: int) -> Tuple[bytes, bytes]:
    return bytes_str[:bytes_len], bytes_str[bytes_len:]


def get_int_from_bytes(bytes_str: bytes) -> Tuple[int, bytes]:
    """ Convert the 4 first bytes into an integer
    Returns
    -------
    int: the decoded integer
    bytes: the remaining bytes string if any
    """
    int_bytes, remaining_bytes = split_nbytes(bytes_str, 4)
    int_obj = bytes_to_int(int_bytes)
    return int_obj, remaining_bytes


def bytes_to_string(message: bytes) -> str:
    return message.decode()


def bytes_to_int(bytes_string: bytes) -> int:
    """Convert a bytes of length 4 into an integer"""
    if not isinstance(bytes_string, bytes):
        raise TypeError(f'{bytes_string} should be an bytes string, not a {type(bytes_string)}')
    assert len(bytes_string) == 4
    return int.from_bytes(bytes_string, 'big')


def bytes_to_scalar(data: bytes, dtype: np.dtype) -> complex:
    """Convert bytes to a scalar given a certain numpy dtype

    Parameters
    ----------
    data: bytes
    dtype:np.dtype

    Returns
    -------
    numbers.Number
    """
    return np.frombuffer(data, dtype=dtype)[0]


def bytes_to_nd_array(data: bytes, dtype: np.dtype, shape: Tuple[int]) -> np.ndarray:
    """Convert bytes to a ndarray given a certain numpy dtype and shape

    Parameters
    ----------
    data: bytes
    dtype: np.dtype
    shape: tuple of int

    Returns
    -------
    np.ndarray
    """
    array = np.frombuffer(data, dtype=dtype)
    array = array.reshape(tuple(shape))
    array = np.atleast_1d(array)  # remove singleton dimensions but keeping ndarrays
    return array


def int_to_bytes(an_integer: int) -> bytes:
    """Convert an unsigned integer into a byte array of length 4 in big endian

    Parameters
    ----------
    an_integer: int

    Returns
    -------
    bytearray
    """
    if not isinstance(an_integer, int):
        raise TypeError(f'{an_integer} should be an integer, not a {type(an_integer)}')
    elif an_integer < 0:
        raise ValueError('Can only serialize unsigned integer using this method')
    return an_integer.to_bytes(4, 'big')


def str_to_bytes(message: str) -> bytes:
    if not isinstance(message, str):
        raise TypeError('Can only serialize str object using this method')
    return message.encode()


def str_len_to_bytes( message: Union[str, bytes]) -> Tuple[bytes, bytes]:
    """ Convert a string and its length to two bytes
    Parameters
    ----------
    message: str
        the message to convert

    Returns
    -------
    bytes: message converted as a byte array
    bytes: length of the message byte array, itself as a byte array of length 4
    """

    if not isinstance(message, str) and not isinstance(message, bytes):
        message = str(message)
    if not isinstance(message, bytes):
        message = str_to_bytes(message)
    return message, int_to_bytes(len(message))
