# -*- coding: utf-8 -*-
"""
Created the 20/10/2023

@author: Sebastien Weber
"""
from enum import Enum
import numbers
from typing import Optional, Tuple, List, Union, TYPE_CHECKING, Any

import numpy as np

from . import utils
from ..serialize.factory import SerializableFactory, SERIALIZABLE, SerializableBase

ser_factory = SerializableFactory()


class NoneSerializeDeserialize(SerializableBase):
    @staticmethod
    def serialize(obj: None) -> bytes:  # type: ignore[override]
        return b""

    @staticmethod
    def deserialize(bytes_str: bytes) -> Tuple[None, bytes]:  # type: ignore[override]
        return None, bytes_str


class StringSerializeDeserialize(SerializableBase):

    @staticmethod
    def serialize(string: str) -> bytes:
        """ Convert a string into a bytes message together with the info to convert it back

        Parameters
        ----------
        string: str

        Returns
        -------
        bytes: the total bytes message to serialize the string
        """
        bytes_string = b''
        cmd_bytes, cmd_length_bytes = utils.str_len_to_bytes(string)
        bytes_string += cmd_length_bytes
        bytes_string += cmd_bytes
        return bytes_string

    @staticmethod
    def deserialize(bytes_str) -> Tuple[str, bytes]:
        """Convert bytes into a str object

        Convert first the fourth first bytes into an int encoding the length of the string to decode

        Returns
        -------
        str: the decoded string
        bytes: the remaining bytes string if any
        """
        string_len, remaining_bytes = utils.get_int_from_bytes(bytes_str)
        str_bytes,  remaining_bytes = utils.split_nbytes(remaining_bytes, string_len)
        str_obj = utils.bytes_to_string(str_bytes)
        return str_obj, remaining_bytes


class BytesSerializeDeserialize(SerializableBase):
    @staticmethod
    def serialize(some_bytes: bytes) -> bytes:
        bytes_string = b''
        bytes_string += utils.int_to_bytes(len(some_bytes))
        bytes_string += some_bytes
        return bytes_string

    @staticmethod
    def deserialize(bytes_str: bytes) -> Tuple[bytes, bytes]:
        bytes_len, remaining_bytes = utils.get_int_from_bytes(bytes_str)
        bytes_str, remaining_bytes = utils.split_nbytes(remaining_bytes, bytes_len)
        return bytes_str, remaining_bytes


class ScalarSerializeDeserialize(SerializableBase):
    @staticmethod
    def serialize(scalar: complex) -> bytes:
        """ Convert a scalar into a bytes message together with the info to convert it back

        Parameters
        ----------
        scalar: A python number (complex or subtypes like float and int)

        Returns
        -------
        bytes: the total bytes message to serialize the scalar
        """
        if not isinstance(scalar, numbers.Number):
            # type hint is complex, instance comparison Number
            raise TypeError(f'{scalar} should be an integer or a float, not a {type(scalar)}')
        scalar_array = np.array([scalar])
        data_type = scalar_array.dtype.descr[0][1]
        data_bytes = scalar_array.tobytes()

        bytes_string = b''
        bytes_string += StringSerializeDeserialize.serialize(data_type)
        bytes_string += utils.int_to_bytes(len(data_bytes))
        bytes_string += data_bytes
        return bytes_string

    @staticmethod
    def deserialize(bytes_str: bytes) -> Tuple[complex, bytes]:
        """Convert bytes into a python object of type (float, int, complex or boolean)

        Get first the data type from a string deserialization, then the data length and finally convert this
        length of bytes into an object of type (float, int, complex or boolean)

        Returns
        -------
        numbers.Number: the decoded number
        bytes: the remaining bytes string if any
        """
        data_type, remaining_bytes = StringSerializeDeserialize.deserialize(bytes_str)
        data_len, remaining_bytes = utils.get_int_from_bytes(remaining_bytes)
        number_bytes, remaining_bytes = utils.split_nbytes(remaining_bytes, data_len)
        number = np.frombuffer(number_bytes, dtype=data_type)[0]
        if 'f' in data_type:
            number = float(number)  # because one get numpy float type
        elif 'i' in data_type:
            number = int(number)  # because one get numpy int type
        elif 'c' in data_type:
            number = complex(number)  # because one get numpy complex type
        elif 'b' in data_type:
            number = bool(number)  # because one get numpy complex type
        return number, remaining_bytes


class NdArraySerializeDeserialize(SerializableBase):

    @staticmethod
    def serialize(array: np.ndarray) -> bytes:
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
        bytes_string += StringSerializeDeserialize.serialize(array_type)
        bytes_string += utils.int_to_bytes(len(array_bytes))
        bytes_string += utils.int_to_bytes(len(array_shape))
        for shape_elt in array_shape:
            bytes_string += utils.int_to_bytes(shape_elt)
        bytes_string += array_bytes
        return bytes_string

    @staticmethod
    def deserialize(bytes_str: bytes) -> Tuple[np.ndarray, bytes]:
        """Convert bytes into a numpy ndarray object

        Convert the first bytes into a ndarray reading first information about the array's data

        Returns
        -------
        ndarray: the decoded numpy array
        bytes: the remaining bytes string if any
        """
        ndarray_type, remaining_bytes = StringSerializeDeserialize.deserialize(bytes_str)
        ndarray_len, remaining_bytes = utils.get_int_from_bytes(remaining_bytes)
        shape_len, remaining_bytes = utils.get_int_from_bytes(remaining_bytes)
        shape = []
        for ind in range(shape_len):
            shape_elt, remaining_bytes = utils.get_int_from_bytes(remaining_bytes)
            shape.append(shape_elt)

        ndarray_bytes, remaining_bytes = utils.split_nbytes(remaining_bytes, ndarray_len)
        ndarray = np.frombuffer(ndarray_bytes, dtype=ndarray_type)
        ndarray = ndarray.reshape(tuple(shape))
        ndarray = np.atleast_1d(ndarray)  # remove singleton dimensions
        return ndarray, remaining_bytes


class ListSerializeDeserialize(SerializableBase):
    @staticmethod
    def serialize(list_object: List) -> bytes:
        """ Convert a list of objects into a bytes message together with the info to convert it back

        Parameters
        ----------
        list_object: list
            the list could contain whatever objects are registered in the SerializableFactory

        Returns
        -------
        bytes: the total bytes message to serialize the list of objects

        Notes
        -----

        The bytes sequence is constructed as:
        * the length of the list

        Then for each object:
        * use the serialization method adapted to each object in the list
        """
        if not isinstance(list_object, list):
            raise TypeError(f'{list_object} should be a list, not a {type(list_object)}')

        bytes_string = b''
        bytes_string += utils.int_to_bytes(len(list_object))
        for obj in list_object:
            bytes_string += ser_factory.get_apply_serializer(obj)
        return bytes_string

    @staticmethod
    def deserialize(bytes_str: bytes) -> Tuple[List[SERIALIZABLE], bytes]:
        """Convert bytes into a list of objects

        Convert the first bytes into a list reading first information about the list elt types, length ...

        Returns
        -------
        list: the decoded list
        bytes: the remaining bytes string if any
        """
        list_obj = []
        list_len, remaining_bytes = utils.get_int_from_bytes(bytes_str)

        for ind in range(list_len):
            obj, remaining_bytes = ser_factory.get_apply_deserializer(remaining_bytes,
                                                                      only_object=False)
            list_obj.append(obj)
        return list_obj, remaining_bytes


class TupleSerializeDeserialize(SerializableBase):
    @staticmethod
    def serialize(tuple_object: Tuple[SERIALIZABLE, ...]) -> bytes:
        """ Convert a tuple of objects into a bytes message together with the info to convert it back

        Parameters
        ----------
        tuple_object: tuple
            the tuple could contain whatever objects are registered in the SerializableFactory

        Returns
        -------
        bytes: the total bytes message to serialize the tuple of objects

        Notes
        -----

        The bytes sequence is constructed as:
        * the length of the tuple

        Then for each object:
        * use the serialization method adapted to each object in the tuple
        """
        if not isinstance(tuple_object, tuple):
            raise TypeError(f'{tuple_object} should be a tuple, not a {type(tuple_object)}')
        return ListSerializeDeserialize().serialize(list(tuple_object))

    @staticmethod
    def deserialize(bytes_str: bytes) -> Tuple[Tuple[SERIALIZABLE, ...], bytes]:
        """Convert bytes into a tuple of objects

        Convert the first bytes into a tuple reading first information about the tuple elt types, length ...

        Returns
        -------
        tuple: the decoded tuple
        bytes: the remaining bytes string if any
        """
        list_object, remaining_bytes = ListSerializeDeserialize().deserialize(bytes_str)
        return tuple(list_object), remaining_bytes


class DictSerializeDeserialize(SerializableBase):
    @staticmethod
    def serialize(dict_object: dict[SERIALIZABLE, SERIALIZABLE]) -> bytes:
        """ Convert a dictionnary of objects into a bytes message together with the info to convert it back

        Parameters
        ----------
        dict_object: dict
            the dict could contain whatever objects are registered in the SerializableFactory

        Returns
        -------
        bytes: the total bytes message to serialize the list of objects

        Notes
        -----

        The bytes sequence is constructed as:
        * the list of keys of the dict

        Then for each key:
        * use the serialization method adapted to the object inferred from the key
        """
        if not isinstance(dict_object, dict):
            raise TypeError(f'{dict_object} should be a dict, not a {type(dict_object)}')

        bytes_string = b''
        keys_list = list(dict_object.keys())
        bytes_string += ser_factory.get_apply_serializer(keys_list)
        for key in keys_list:
            bytes_string += ser_factory.get_apply_serializer(dict_object[key])
        return bytes_string

    @staticmethod
    def deserialize(bytes_str: bytes) -> Tuple[dict[str, SERIALIZABLE], bytes]:
        """Convert bytes into a dictionary of serializable objects

        Convert the first bytes into a dict reading first information about the key elts of the dictionnary then
        the underlying objects ...

        Returns
        -------
        dict: the decoded dictionary
        bytes: the remaining bytes string if any
        """
        dict_object = {}
        keys_list, remaining_bytes = ser_factory.get_apply_deserializer(bytes_str,
                                                                        only_object=False)

        for key in keys_list:
            obj, remaining_bytes = ser_factory.get_apply_deserializer(remaining_bytes,
                                                                      only_object=False)
            dict_object[key] = obj
        return dict_object, remaining_bytes


ser_factory.register_from_type(
    type(None), NoneSerializeDeserialize.serialize, NoneSerializeDeserialize.deserialize
)
ser_factory.register_from_type(bytes,
                                       BytesSerializeDeserialize.serialize,
                                       BytesSerializeDeserialize.deserialize)
ser_factory.register_from_type(str, StringSerializeDeserialize.serialize,
                                       StringSerializeDeserialize.deserialize)
ser_factory.register_from_type(int, ScalarSerializeDeserialize.serialize,
                                       ScalarSerializeDeserialize.deserialize)
ser_factory.register_from_type(float, ScalarSerializeDeserialize.serialize,
                                       ScalarSerializeDeserialize.deserialize)
ser_factory.register_from_obj(1 + 1j, ScalarSerializeDeserialize.serialize,
                                      ScalarSerializeDeserialize.deserialize)
ser_factory.register_from_type(bool, ScalarSerializeDeserialize.serialize,
                                       ScalarSerializeDeserialize.deserialize)
ser_factory.register_from_obj(np.array([0, 1]),
                                      NdArraySerializeDeserialize.serialize,
                                      NdArraySerializeDeserialize.deserialize)
ser_factory.register_from_type(list,
                               ListSerializeDeserialize.serialize,
                               ListSerializeDeserialize.deserialize)

ser_factory.register_from_type(tuple,
                               TupleSerializeDeserialize.serialize,
                               TupleSerializeDeserialize.deserialize)

ser_factory.register_from_type(dict,
                               DictSerializeDeserialize.serialize,
                               DictSerializeDeserialize.deserialize)

class SerializableTypes(Enum):
    """Type names of serializable types"""
    NONE = "NoneType"  # just in case it is needed
    BOOL = "bool"
    BYTES = "bytes"
    STRING = "string"
    SCALAR = "scalar"
    LIST = "list"
    TUPLE = 'tuple'
    DICT = 'dict'
    ARRAY = "array"
    AXIS = "axis"
    DATA_WITH_AXES = "dwa"
    DATA_TO_EXPORT = "dte"
    PARAMETER = "parameter"




