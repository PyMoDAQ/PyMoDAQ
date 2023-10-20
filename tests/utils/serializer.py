# -*- coding: utf-8 -*-
"""
Created the 20/10/2023

@author: Sebastien Weber
"""
import numbers
from typing import Tuple, List, Union


import numpy as np

from pymodaq.utils.data import DataWithAxes, DataToExport, Axis


class Serializer:
    """Used to Serialize to bytes python objects, numpy arrays and PyMoDAQ DataWithAxes and DataToExport objects"""

    @staticmethod
    def int_to_bytes(an_integer: int) -> bytes:
        """Convert an integer into a byte array of length 4 in big endian

        Parameters
        ----------
        an_integer: int

        Returns
        -------
        bytearray
        """
        if not isinstance(an_integer, int):
            raise TypeError(f'{an_integer} should be an integer, not a {type(an_integer)}')
        return an_integer.to_bytes(4, 'big')


    @staticmethod
    def str_to_bytes(message: str) -> bytes:
        message.encode()

    @classmethod
    def str_len_to_bytes(cls, message: str) -> (bytes, bytes):
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
            message = cls.str_to_bytes(message)
        return message, cls.int_to_bytes(len(message))

    @staticmethod
    def bytes_to_string(message: bytes) -> str:
        return message.decode()

    @staticmethod
    def ndarray_dtype_as_string(data: np.ndarray) -> str:
        """Convert a numpy array dtype into its string representation
        """
        return data.dtype.descr[0][1]

    @staticmethod
    def scalar_to_bytes(data: numbers.Number) -> bytes:
        """Convert a Number into a numpy array then to bytes using numpy features"""
        if not isinstance(data, numbers.Number):
            raise TypeError(f'{data} should be an integer or a float, not a {type(data)}')
        data = np.array([data])
        return data.tobytes()

    @staticmethod
    def bytes_to_scalar(data: bytes, dtype: np.dtype) -> numbers.Number:
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

    @staticmethod
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
        array = np.atleast_1d(array)  # remove singleton dimensions
        return array

    @classmethod
    def string_serialization(cls, string: str) -> bytes:
        """ Convert a string into a bytes message together with the info to convert it back

        Parameters
        ----------
        string: str

        Returns
        -------
        bytes: the total bytes message to serialize the string
        """
        bytes_string = b''
        cmd_bytes, cmd_length_bytes = cls.str_len_to_bytes(string)
        bytes_string += cmd_length_bytes
        bytes_string += cmd_bytes
        return bytes_string

    @classmethod
    def scalar_serialization(cls, scalar: numbers.Number) -> bytes:
        """ Convert a scalar into a bytes message together with the info to convert it back

        Parameters
        ----------
        scalar: str

        Returns
        -------
        bytes: the total bytes message to serialize the scalar
        """
        if not isinstance(scalar, numbers.Number) :
            raise TypeError(f'{scalar} should be an integer or a float, not a {type(scalar)}')
        scalar_array = np.array([scalar])
        data_type = scalar_array.dtype.descr[0][1]
        data_bytes = scalar_array.tobytes()

        bytes_string = b''
        bytes_string += data_type
        bytes_string += cls.int_to_bytes(len(data_bytes))
        bytes_string += data_bytes
        return bytes_string

    @classmethod
    def array_serialization(cls, array: np.ndarray) -> bytes:
        """ Convert a ndarray into a bytes message together with the info to convert it back

        Parameters
        ----------
        array: np.ndarray

        Returns
        -------
        bytes: the total bytes message to serialize the scalar

        Notes
        -----

        The bytes sequence is constructed as:

        * get data type as a string
        * reshape array as 1D array and get the array dimensionality (len of array's shape)
        * convert Data array as bytes
        * serialize data type
        * serialize data length
        * serialize data shape length
        * serialize all values of the shape as integers converted to bytes
        * serialize array as bytes
        """
        if not isinstance(array, np.ndarray):
            raise TypeError(f'{array} should be an numpy array, not a {type(array)}')
        array_type = array.dtype.descr[0][1]
        array_shape = array.shape

        array = array.reshape(array.size)
        array_bytes = array.tobytes()
        bytes_string = b''
        bytes_string += array_type
        bytes_string += cls.int_to_bytes(len(array_bytes))
        bytes_string += cls.int_to_bytes(len(array_shape))
        for shape_elt in array_shape:
            bytes_string += cls.int_to_bytes(shape_elt)
        bytes_string += array_bytes
        return bytes_string

    @classmethod
    def object_type_serialization(cls, obj: Union[Axis, DataToExport, DataWithAxes]) -> bytes:
        """ Convert an object type into a bytes message as a string together with the info to convert it back

        Applies to Data object from the pymodaq.utils.data module
        """
        return cls.string_serialization(obj.__class__.__name__)

    @classmethod
    def axis_serialization(cls, axis: Axis) -> bytes:
        """ Convert an Axis object into a bytes message together with the info to convert it back

        Parameters
        ----------
        axis: Axis

        Returns
        -------
        bytes: the total bytes message to serialize the Axis

        Notes
        -----

        The bytes sequence is constructed as:

        * serialize the type: 'Axis'
        * serialize the axis label
        * serialize the axis units
        * serialize the axis array
        * serialize the axis index
        """
        if not isinstance(axis, Axis):
            raise TypeError(f'{axis} should be a list, not a {type(axis)}')

        bytes_string = b''
        bytes_string += cls.object_type_serialization(axis)
        bytes_string += cls.string_serialization(axis.label)
        bytes_string += cls.string_serialization(axis.units)
        bytes_string += cls.array_serialization(axis.get_data())
        bytes_string += cls.scalar_serialization(axis.index)
        return bytes_string

    @classmethod
    def list_serialization(cls, list_object: List) -> bytes:
        """ Convert a list of objects into a bytes message together with the info to convert it back

        Parameters
        ----------
        list_object: list
            the list could contains either scalars, strings or ndarrays or Axis objects or DataWithAxis objects
            module

        Returns
        -------
        bytes: the total bytes message to serialize the list of objects

        Notes
        -----

        The bytes sequence is constructed as:
        * the length of the list
        * get data type as a string
        * reshape array as 1D array and get the array dimensionality (len of array's shape)
        * convert Data array as bytes
        * serialize data type
        * serialize data length
        * serialize data shape length
        * serialize all values of the shape as integers converted to bytes
        * serialize array as bytes
        """
        if not isinstance(list_object, list):
            raise TypeError(f'{list_object} should be a list, not a {type(list_object)}')

        bytes_string = b''

        bytes_string += cls.int_to_bytes(len(list_object))
        for obj in list_object:
            if isinstance(obj, DataWithAxes):
                bytes_string += cls.string_serialization('dwa')
                bytes_string += cls.dwa_serialization(obj)

            elif isinstance(obj, Axis):
                bytes_string += cls.string_serialization('axis')
                bytes_string += cls.axis_serialization(obj)

            elif isinstance(obj, np.ndarray):
                bytes_string += cls.string_serialization('array')
                bytes_string += cls.array_serialization(obj)

            elif isinstance(obj, str):
                bytes_string += cls.string_serialization('string')
                bytes_string += cls.string_serialization(obj)

            elif isinstance(obj, numbers.Number):
                bytes_string += cls.string_serialization('scalar')
                bytes_string += cls.scalar_serialization(obj)

            else:
                raise TypeError(f'the element {obj} type cannot be serialized into bytes, only numpy arrays'
                                f', strings, or scalars (int or float)')

    @classmethod
    def dwa_serialization(cls, dwa: DataWithAxes) -> bytes:
        """ Convert a DataWithAxes into a bytes string

        Parameters
        ----------
        dwa: DataWithAxes

        Returns
        -------
        bytes: the total bytes message to serialize the DataWithAxes

        Notes
        -----
        The bytes sequence is constructed as:

        * serialize the string type: 'DataWithAxis'
        * serialize the name
        * serialize the source enum as a string
        * serialize the dim enum as a string
        * serialize the distribution enum as a string
        * serialize the list of numpy arrays
        * serialize the list of labels
        * serialize the origin
        * serialize the nav_index tuple as a list of int
        * serialize the list of axis
        """
        if not isinstance(dwa, DataWithAxes):
            raise TypeError(f'{dwa} should be a list, not a {type(dwa)}')

        bytes_string = b''
        bytes_string += cls.object_type_serialization(dwa)
        bytes_string += cls.string_serialization(dwa.name)
        bytes_string += cls.string_serialization(dwa.source.name)
        bytes_string += cls.string_serialization(dwa.dim.name)
        bytes_string += cls.string_serialization(dwa.distribution.name)
        bytes_string += cls.list_serialization(dwa.data)
        bytes_string += cls.list_serialization(dwa.labels)
        bytes_string += cls.string_serialization(dwa.origin)
        bytes_string += cls.list_serialization(list(dwa.nav_indexes))
        bytes_string += cls.list_serialization(dwa.axes)
        return bytes_string


class DeSerializer:


    @staticmethod
    def bytes_to_int(bytes_string: bytes) -> int:
        """Convert a bytes of length 4 into an integer"""
        if not isinstance(bytes_string, bytes):
            raise TypeError(f'{bytes_string} should be an bytes string, not a {type(bytes_string)}')
        assert len(bytes_string) == 4
        return int.from_bytes(bytes_string, 'big')

    @classmethod
    def int_deserialisation(cls, bytes_string: bytes) -> Tuple[int, bytes]:
        """Convert the fourth first bytes into an integer returning the rest of the string"""
        return cls.bytes_to_int(bytes_string[0:4]), bytes_string[4:]

    @classmethod
    def string_deserialization(cls, bytes_string: bytes) -> str:
        string_len, bytes_string = cls.int_deserialisation(bytes_string)
        return bytes_string[0:string_len].decode(), bytes_string[string_len:]

    def get_scalar(self):
        """

        Parameters
        ----------
        socket

        Returns
        -------

        """
        data_type = self.get_string()
        data_len = self.get_int()
        data_bytes = self.check_received_length(data_len)

        data = np.frombuffer(data_bytes, dtype=data_type)[0]
        return data

    def get_array(self):
        """get 1D or 2D arrays"""
        data_type = self.get_string()
        data_len = self.get_int()
        shape_len = self.get_int()
        shape = []
        for ind in range(shape_len):
            shape.append(self.get_int())
        data_bytes = self.check_received_length(data_len)
        data = np.frombuffer(data_bytes, dtype=data_type)
        data = data.reshape(tuple(shape))
        data = np.squeeze(data)  # remove singleton dimensions
        return data

    def get_list(self):
        """
        Receive data from socket as a list
        Parameters
        ----------
        socket: the communication socket
        Returns
        -------

        """
        data = []
        list_len = self.get_int()

        for ind in range(list_len):
            data_type = self.get_string()
            if data_type == 'scalar':
                data.append(self.get_scalar())
            elif data_type == 'string':
                data.append(self.get_string())
            elif data_type == 'array':
                data.append(self.get_array())
        return data

