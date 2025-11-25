import numpy as np
from base64 import b64encode, b64decode

from typing import Optional, Union, Any, List, TYPE_CHECKING
from .mysocket import SocketString, Socket
from . import utils

from pymodaq_utils.serialize.factory import SerializableFactory, SERIALIZABLE

ser_factory = SerializableFactory()

if TYPE_CHECKING:
    from pymodaq_data.data import (Axis, DataWithAxes, DataToExport)


class Serializer:
    """Used to Serialize to bytes python objects, numpy arrays and PyMoDAQ DataWithAxes and
    DataToExport objects

    Deprecated in PyMoDAQ >= 5 use the SerializerFactory object
    """

    def __init__(self, obj: Optional[SERIALIZABLE] = None) -> None:
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
        return ser_factory.get_apply_serializer(self._obj, append_length=True)

    def to_b64_string(self) -> str:
        b = self.to_bytes()
        return b64encode(b).decode()

    def bytes_serialization(self, bytes_string_in: bytes) -> bytes:
        """ Convert a bytes string into a bytes message together with the info to convert it back"""

        return ser_factory.get_apply_serializer(bytes_string_in, append_length=True)

    def string_serialization(self, string: str) -> bytes:
        """ Convert a string into a bytes message together with the info to convert it back

        Parameters
        ----------
        string: str

        Returns
        -------
        bytes: the total bytes message to serialize the string
        """
        return ser_factory.get_apply_serializer(string, append_length=True)

    def scalar_serialization(self, scalar: complex) -> bytes:
        """ Convert a scalar into a bytes message together with the info to convert it back

        Parameters
        ----------
        scalar: A python number (complex or subtypes like float and int)

        Returns
        -------
        bytes: the total bytes message to serialize the scalar
        """
        return ser_factory.get_apply_serializer(scalar, append_length=True)

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
        return ser_factory.get_apply_serializer(array, append_length=True)

    def object_type_serialization(self, obj: Any) -> bytes:
        """ Convert an object type into a bytes message as a string together with the info to
        convert it back

        """
        return ser_factory.get_apply_serializer(obj.__class__.__name__)

    def axis_serialization(self, axis: 'Axis') -> bytes:
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
        return ser_factory.get_apply_serializer(axis, append_length=True)

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
        return ser_factory.get_apply_serializer(list_object, append_length=True)

    def dwa_serialization(self, dwa: 'DataWithAxes') -> bytes:
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
        * serialize the errors attributes (None or list(np.ndarray))
        * serialize the list of names of extra attributes
        * serialize the extra attributes
        """
        return ser_factory.get_apply_serializer(dwa, append_length=True)

    def dte_serialization(self, dte: 'DataToExport') -> bytes:
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
        return ser_factory.get_apply_serializer(dte, append_length=True)

    def type_and_object_serialization(
            self, obj: Optional[SERIALIZABLE] = None) -> bytes:
        """Serialize an object with its type, such that it can be retrieved by
        `DeSerializer.type_and_object_deserialization`.
        """

        if obj is None and self._obj is not None:
            obj = self._obj

        return ser_factory.get_apply_serializer(obj, append_length=True)


class DeSerializer:
    """Used to DeSerialize bytes to python objects, numpy arrays and PyMoDAQ Axis,
     DataWithAxes and DataToExport
    objects

    Parameters
    ----------
    bytes_string: bytes or Socket
        the bytes string to deserialize into an object: int, float, string, arrays, list, Axis, DataWithAxes...
        Could also be a Socket object reading bytes from the network having a `get_first_nbytes` method

    See Also
    --------
    :py:class:`~pymodaq_data.serialize.mysocket.SocketString`
    :py:class:`~pymodaq_data.serialize.mysocket.Socket`
    """

    def __init__(self, bytes_string:  Union[bytes, Socket,] = None) -> None:
        if isinstance(bytes_string, bytes):
            bytes_string = SocketString(bytes_string)
        self._bytes_string = bytes_string

    def get_message_length(self) -> int:
        return utils.bytes_to_int(self._bytes_string.check_received_length(4))

    @classmethod
    def from_b64_string(cls, b64_string: Union[bytes, str]) -> "DeSerializer":
        return cls(b64decode(b64_string))

    def bytes_deserialization(self) -> bytes:
        bstring_len = self.get_message_length()
        bytes_str = self._bytes_string.check_received_length(bstring_len)
        bstr, _ = ser_factory.get_apply_deserializer(bytes_str)
        return bstr

    def string_deserialization(self) -> str:
        """Convert bytes into a str object

        Convert first the fourth first bytes into an int encoding the length of the string to decode

        Returns
        -------
        str: the decoded string
        """
        bstring_len = self.get_message_length()
        bytes_str = self._bytes_string.check_received_length(bstring_len)
        str_obj = ser_factory.get_apply_deserializer(bytes_str)
        return str_obj

    def scalar_deserialization(self) -> complex:
        """Convert bytes into a python number object

        Get first the data type from a string deserialization, then the data length and finally convert this
        length of bytes into a number (float, int)

        Returns
        -------
        numbers.Number: the decoded number
        """
        bstring_len = self.get_message_length()
        bytes_str = self._bytes_string.check_received_length(bstring_len)
        scalar = ser_factory.get_apply_deserializer(bytes_str)
        return scalar

    def boolean_deserialization(self) -> bool:
        """Convert bytes into a boolean object

        Get first the data type from a string deserialization, then the data length and finally
        convert this length of bytes into a number (float, int) and cast it to a bool

        Returns
        -------
        bool: the decoded boolean
        """
        return bool(self.scalar_deserialization())

    def ndarray_deserialization(self) -> np.ndarray:
        """Convert bytes into a numpy ndarray object

        Convert the first bytes into a ndarray reading first information about the array's data

        Returns
        -------
        ndarray: the decoded numpy array
        """
        bstring_len = self.get_message_length()
        bytes_str = self._bytes_string.check_received_length(bstring_len)
        array = ser_factory.get_apply_deserializer(bytes_str)
        return array

    def type_and_object_deserialization(self) -> SERIALIZABLE:
        """ Deserialize specific objects from their binary representation (inverse of `Serializer.type_and_object_serialization`).

        See Also
        --------
        Serializer.dwa_serialization, Serializer.dte_serialization

        """
        bstring_len = self.get_message_length()
        bytes_str = self._bytes_string.check_received_length(bstring_len)
        obj = ser_factory.get_apply_deserializer(bytes_str)
        return obj

    def list_deserialization(self) -> list:
        """Convert bytes into a list of homogeneous objects

        Convert the first bytes into a list reading first information about the list elt types, length ...

        Returns
        -------
        list: the decoded list
        """
        bstring_len = self.get_message_length()
        bytes_str = self._bytes_string.check_received_length(bstring_len)
        obj = ser_factory.get_apply_deserializer(bytes_str)
        return obj

    def parameter_deserialization(self):
        bstring_len = self.get_message_length()
        bytes_str = self._bytes_string.check_received_length(bstring_len)
        obj = ser_factory.get_apply_deserializer(bytes_str)
        return obj

    def axis_deserialization(self) -> 'Axis':
        """Convert bytes into an Axis object

        Convert the first bytes into an Axis reading first information about the Axis

        Returns
        -------
        Axis: the decoded Axis
        """

        bstring_len = self.get_message_length()
        bytes_str = self._bytes_string.check_received_length(bstring_len)
        obj = ser_factory.get_apply_deserializer(bytes_str)
        return obj

    def dwa_deserialization(self) -> 'DataWithAxes':
        """Convert bytes into a DataWithAxes object

        Convert the first bytes into a DataWithAxes reading first information about the underlying data

        Returns
        -------
        DataWithAxes: the decoded DataWithAxes
        """
        bstring_len = self.get_message_length()
        bytes_str = self._bytes_string.check_received_length(bstring_len)
        obj = ser_factory.get_apply_deserializer(bytes_str)
        return obj

    def dte_deserialization(self) -> 'DataToExport':
        """Convert bytes into a DataToExport object

        Convert the first bytes into a DataToExport reading first information about the underlying data

        Returns
        -------
        DataToExport: the decoded DataToExport
        """
        bstring_len = self.get_message_length()
        bytes_str = self._bytes_string.check_received_length(bstring_len)
        obj = ser_factory.get_apply_deserializer(bytes_str)
        return obj
