# -*- coding: utf-8 -*-
"""
Created the 20/10/2023

@author: Sebastien Weber
"""
import numbers
from typing import Tuple, List, Union, TYPE_CHECKING


import numpy as np
from pymodaq.utils import data as data_mod
from pymodaq.utils.data import DataWithAxes, DataToExport, Axis, DwaType

if TYPE_CHECKING:
    from pymodaq.utils.tcp_ip.mysocket import Socket


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


class Serializer:
    """Used to Serialize to bytes python objects, numpy arrays and PyMoDAQ DataWithAxes and DataToExport objects"""

    def __init__(self, obj: Union[int, str, numbers.Number, list, np.ndarray, Axis, DataWithAxes, DataToExport] = None):
        self._bytes_string = b''
        self._obj = obj

    def to_bytes(self):
        """ Generic method to obtain the bytes string from various objects

        Compatible objects are:

        * :class:`bytes`
        * :class:`numbers.Number`
        * :class:`str`
        * :class:`numpy.ndarray`
        * :class:`~pymodaq.utils.data.Axis`
        * :class:`~pymodaq.utils.data.DataWithAxes` and sub-flavours
        * :class:`~pymodaq.utils.data.DataToExport`
        * :class:`list` of any objects above

        """
        if isinstance(self._obj, bytes):
            return self.bytes_serialization(self._obj)
        elif isinstance(self._obj, numbers.Number):
            return self.scalar_serialization(self._obj)
        elif isinstance(self._obj, str):
            return self.string_serialization(self._obj)
        elif isinstance(self._obj, np.ndarray):
            return self.ndarray_serialization(self._obj)
        elif isinstance(self._obj, Axis):
            return self.axis_serialization(self._obj)
        elif self._obj.__class__.__name__ in DwaType.names():
            return self.dwa_serialization(self._obj)
        elif isinstance(self._obj, DataToExport):
            return self.dte_serialization(self._obj)
        elif isinstance(self._obj, list):
            return self.list_serialization(self._obj)

    @staticmethod
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
            raise ValueError(f'Can only serialize unsigned integer using this method')
        return an_integer.to_bytes(4, 'big')

    @staticmethod
    def str_to_bytes(message: str) -> bytes:
        if not isinstance(message, str):
            raise TypeError(f'Can only serialize str object using this method')
        return message.encode()

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

    def _int_serialization(self, int_obj: int) -> bytes:
        """serialize an unsigned integer used for getting the length of messages internaly, for outside integer
        serialization or deserialization use scalar_serialization"""
        int_bytes = self.int_to_bytes(int_obj)
        bytes_string = int_bytes
        self._bytes_string += bytes_string
        return bytes_string

    def bytes_serialization(self, bytes_string_in: bytes) -> bytes:
        bytes_string = b''
        bytes_string += self.int_to_bytes(len(bytes_string_in))
        bytes_string += bytes_string_in
        return bytes_string

    def string_serialization(self, string: str) -> bytes:
        """ Convert a string into a bytes message together with the info to convert it back

        Parameters
        ----------
        string: str

        Returns
        -------
        bytes: the total bytes message to serialize the string
        """
        bytes_string = b''
        cmd_bytes, cmd_length_bytes = self.str_len_to_bytes(string)
        bytes_string += cmd_length_bytes
        bytes_string += cmd_bytes
        self._bytes_string += bytes_string
        return bytes_string

    def scalar_serialization(self, scalar: numbers.Number) -> bytes:
        """ Convert a scalar into a bytes message together with the info to convert it back

        Parameters
        ----------
        scalar: str

        Returns
        -------
        bytes: the total bytes message to serialize the scalar
        """
        if not isinstance(scalar, numbers.Number):
            raise TypeError(f'{scalar} should be an integer or a float, not a {type(scalar)}')
        scalar_array = np.array([scalar])
        data_type = scalar_array.dtype.descr[0][1]
        data_bytes = scalar_array.tobytes()

        bytes_string = b''
        bytes_string += self.string_serialization(data_type)
        bytes_string += self._int_serialization(len(data_bytes))
        bytes_string += data_bytes
        self._bytes_string += bytes_string
        return bytes_string

    def ndarray_serialization(self, array: np.ndarray) -> bytes:
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
        bytes_string += self.string_serialization(array_type)
        bytes_string += self._int_serialization(len(array_bytes))
        bytes_string += self._int_serialization(len(array_shape))
        for shape_elt in array_shape:
            bytes_string += self._int_serialization(shape_elt)
        bytes_string += array_bytes
        self._bytes_string += bytes_string
        return bytes_string

    def object_type_serialization(self, obj: Union[Axis, DataToExport, DataWithAxes]) -> bytes:
        """ Convert an object type into a bytes message as a string together with the info to convert it back

        Applies to Data object from the pymodaq.utils.data module
        """
        return self.string_serialization(obj.__class__.__name__)

    def axis_serialization(self, axis: Axis) -> bytes:
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
        * serialize the axis
        * serialize the axis spread_order
        """
        if not isinstance(axis, Axis):
            raise TypeError(f'{axis} should be a list, not a {type(axis)}')

        bytes_string = b''
        bytes_string += self.object_type_serialization(axis)
        bytes_string += self.string_serialization(axis.label)
        bytes_string += self.string_serialization(axis.units)
        bytes_string += self.ndarray_serialization(axis.get_data())
        bytes_string += self.scalar_serialization(axis.index)
        bytes_string += self.scalar_serialization(axis.spread_order)
        self._bytes_string += bytes_string
        return bytes_string

    def list_serialization(self, list_object: List) -> bytes:
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

        Then for each object:

        * get data type as a string
        * use the serialization method adapted to each object in the list
        """
        if not isinstance(list_object, list):
            raise TypeError(f'{list_object} should be a list, not a {type(list_object)}')

        bytes_string = b''

        bytes_string += self._int_serialization(len(list_object))
        for obj in list_object:
            if isinstance(obj, DataWithAxes):
                bytes_string += self.string_serialization('dwa')
                bytes_string += self.dwa_serialization(obj)

            elif isinstance(obj, Axis):
                bytes_string += self.string_serialization('axis')
                bytes_string += self.axis_serialization(obj)

            elif isinstance(obj, np.ndarray):
                bytes_string += self.string_serialization('array')
                bytes_string += self.ndarray_serialization(obj)

            elif isinstance(obj, str):
                bytes_string += self.string_serialization('string')
                bytes_string += self.string_serialization(obj)

            elif isinstance(obj, numbers.Number):
                bytes_string += self.string_serialization('scalar')
                bytes_string += self.scalar_serialization(obj)

            else:
                raise TypeError(f'the element {obj} type cannot be serialized into bytes, only numpy arrays'
                                f', strings, or scalars (int or float)')
        self._bytes_string += bytes_string
        return bytes_string

    def dwa_serialization(self, dwa: DataWithAxes) -> bytes:
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

        * serialize the string type: 'DataWithAxes'
        * serialize the timestamp: float
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
            raise TypeError(f'{dwa} should be a DataWithAxes, not a {type(dwa)}')

        bytes_string = b''
        bytes_string += self.object_type_serialization(dwa)
        bytes_string += self.scalar_serialization(dwa.timestamp)
        bytes_string += self.string_serialization(dwa.name)
        bytes_string += self.string_serialization(dwa.source.name)
        bytes_string += self.string_serialization(dwa.dim.name)
        bytes_string += self.string_serialization(dwa.distribution.name)
        bytes_string += self.list_serialization(dwa.data)
        bytes_string += self.list_serialization(dwa.labels)
        bytes_string += self.string_serialization(dwa.origin)
        bytes_string += self.list_serialization(list(dwa.nav_indexes))
        bytes_string += self.list_serialization(dwa.axes)
        self._bytes_string += bytes_string
        return bytes_string

    def dte_serialization(self, dte: DataToExport) -> bytes:
        """ Convert a DataToExport into a bytes string

        Parameters
        ----------
        dte: DataToExport

        Returns
        -------
        bytes: the total bytes message to serialize the DataToExport

        Notes
        -----
        The bytes sequence is constructed as:

        * serialize the string type: 'DataToExport'
        * serialize the timestamp: float
        * serialize the name
        * serialize the list of DataWithAxes
        """
        if not isinstance(dte, DataToExport):
            raise TypeError(f'{dte} should be a DataToExport, not a {type(dte)}')

        bytes_string = b''
        bytes_string += self.object_type_serialization(dte)
        bytes_string += self.scalar_serialization(dte.timestamp)
        bytes_string += self.string_serialization(dte.name)
        bytes_string += self.list_serialization(dte.data)
        self._bytes_string += bytes_string
        return bytes_string


class DeSerializer:
    """Used to DeSerialize bytes to python objects, numpy arrays and PyMoDAQ Axis, DataWithAxes and DataToExport
    objects

    Parameters
    ----------
    bytes_string: bytes or Socket
        the bytes string to deserialize into an object: int, float, string, arrays, list, Axis, DataWithAxes...
        Could also be a Socket object reading bytes from the network having a `get_first_nbytes` method

    See Also
    --------
    :py:class:`~pymodaq.utils.tcp_ip.serializer.SocketString`
    :py:class:`~pymodaq.utils.tcp_ip.mysocket.Socket`
    """

    def __init__(self, bytes_string:  Union[bytes, 'Socket'] = None):
        if isinstance(bytes_string, bytes):
            bytes_string = SocketString(bytes_string)
        self._bytes_string = bytes_string

    @staticmethod
    def bytes_to_string(message: bytes) -> str:
        return message.decode()

    @staticmethod
    def bytes_to_int(bytes_string: bytes) -> int:
        """Convert a bytes of length 4 into an integer"""
        if not isinstance(bytes_string, bytes):
            raise TypeError(f'{bytes_string} should be an bytes string, not a {type(bytes_string)}')
        assert len(bytes_string) == 4
        return int.from_bytes(bytes_string, 'big')

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
        array = np.atleast_1d(array)  # remove singleton dimensions but keeping ndarrays
        return array

    def _int_deserialization(self) -> int:
        """Convert the fourth first bytes into an unsigned integer to be used internally. For integer serialization
        use scal_serialization"""
        int_obj = self.bytes_to_int(self._bytes_string.get_first_nbytes(4))
        return int_obj

    def string_deserialization(self) -> str:
        """Convert bytes into a str object

        Convert first the fourth first bytes into an int encoding the length of the string to decode

        Returns
        -------
        str: the decoded string
        """
        string_len = self._int_deserialization()
        str_obj = self._bytes_string.get_first_nbytes(string_len).decode()
        return str_obj

    def scalar_deserialization(self) -> numbers.Number:
        """Convert bytes into a numbers.Number object

        Get first the data type from a string deserialization, then the data length and finally convert this
        length of bytes into a number (float, int)

        Returns
        -------
        numbers.Number: the decoded number
        """
        data_type = self.string_deserialization()
        data_len = self._int_deserialization()
        number = np.frombuffer(self._bytes_string.get_first_nbytes(data_len), dtype=data_type)[0]
        if 'f' in data_type:
            number = float(number)  # because one get numpy  float type
        elif 'i' in data_type:
            number = int(number)  # because one get numpy int type
        return number

    def ndarray_deserialization(self) -> np.ndarray:
        """Convert bytes into a numpy ndarray object

        Convert the first bytes into a ndarray reading first information about the array's data

        Returns
        -------
        ndarray: the decoded numpy array
        """
        ndarray_type = self.string_deserialization()
        ndarray_len = self._int_deserialization()
        shape_len = self._int_deserialization()
        shape = []
        for ind in range(shape_len):
            shape_elt = self._int_deserialization()
            shape.append(shape_elt)

        ndarray = np.frombuffer(self._bytes_string.get_first_nbytes(ndarray_len), dtype=ndarray_type)
        ndarray = ndarray.reshape(tuple(shape))
        ndarray = np.atleast_1d(ndarray)  # remove singleton dimensions
        return ndarray

    def list_deserialization(self) -> list:
        """Convert bytes into a list of homogeneous objects

        Convert the first bytes into a list reading first information about the list elt types, length ...

        Returns
        -------
        list: the decoded list
        """
        list_obj = []
        list_len = self._int_deserialization()

        for ind in range(list_len):
            obj_type = self.string_deserialization()
            if obj_type == 'scalar':
                list_elt = self.scalar_deserialization()
            elif obj_type == 'string':
                list_elt = self.string_deserialization()
            elif obj_type == 'array':
                list_elt = self.ndarray_deserialization()
            elif obj_type == 'dwa':
                list_elt = self.dwa_deserialization()
            elif obj_type == 'axis':
                list_elt = self.axis_deserialization()
            list_obj.append(list_elt)
        return list_obj

    def axis_deserialization(self) -> Axis:
        """Convert bytes into an Axis object

        Convert the first bytes into an Axis reading first information about the Axis

        Returns
        -------
        Axis: the decoded Axis
        """

        class_name = self.string_deserialization()
        if class_name != Axis.__name__:
            raise TypeError(f'Attempting to deserialize an Axis but got the bytes for a {class_name}')
        axis_label = self.string_deserialization()
        axis_units = self.string_deserialization()
        axis_array = self.ndarray_deserialization()
        axis_index = self.scalar_deserialization()
        axis_spread_order = self.scalar_deserialization()

        axis = Axis(axis_label, axis_units, data=axis_array, index=axis_index, spread_order=axis_spread_order)
        return axis

    def dwa_deserialization(self) -> DataWithAxes:
        """Convert bytes into a DataWithAxes object

        Convert the first bytes into a DataWithAxes reading first information about the underlying data

        Returns
        -------
        DataWithAxes: the decoded DataWithAxes
        """
        class_name = self.string_deserialization()
        if class_name not in DwaType.names():
            raise TypeError(f'Attempting to deserialize a DataWithAxes flavor but got the bytes for a {class_name}')
        timestamp = self.scalar_deserialization()
        dwa = getattr(data_mod, class_name)(self.string_deserialization(),
                                            source=self.string_deserialization(),
                                            dim=self.string_deserialization(),
                                            distribution=self.string_deserialization(),
                                            data=self.list_deserialization(),
                                            labels=self.list_deserialization(),
                                            origin=self.string_deserialization(),
                                            nav_indexes=tuple(self.list_deserialization()),
                                            axes=self.list_deserialization(),
                                            )
        dwa.timestamp = timestamp
        return dwa

    def dte_deserialization(self) -> DataToExport:
        """Convert bytes into a DataToExport object

        Convert the first bytes into a DataToExport reading first information about the underlying data

        Returns
        -------
        DataToExport: the decoded DataToExport
        """
        class_name = self.string_deserialization()
        if class_name != DataToExport.__name__:
            raise TypeError(f'Attempting to deserialize a DataToExport but got the bytes for a {class_name}')
        timestamp = self.scalar_deserialization()
        dte = DataToExport(self.string_deserialization(),
                           data=self.list_deserialization(),
                           )
        dte.timestamp = timestamp
        return dte