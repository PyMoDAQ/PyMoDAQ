from abc import ABCMeta, abstractmethod
from typing import Callable, List, Any, Optional, Tuple, TypeVar, Union

from numpy.typing import NDArray

from . import utils


class SerializableBase(metaclass=ABCMeta):
    """Base class for a Serializer. """

    @classmethod
    def name(cls):
        """str: the object class name"""
        return cls.__class__.__name__

    @classmethod
    def type(cls):
        """object: the type of the object"""
        return cls.__class__

    @staticmethod
    @abstractmethod
    def serialize(obj: "SerializableBase") -> bytes:
        """  Implements self serialization into bytes

        Parameters
        ----------
        obj: SerializableBase

        Returns
        -------
        bytes

        Notes
        -----
        The actual serialization should be done using the SerializableFactory and its method
        :meth:SerializableFactory.get_apply_serializer
        """
        ...

    @staticmethod
    @abstractmethod
    def deserialize(bytes_str: bytes) -> Tuple["SerializableBase", bytes]:
        """ Implements deserialization into self type from bytes

        Parameters
        ----------
        bytes_str: bytes

        Returns
        -------
        SerializableBase: object to reconstruct
        bytes: leftover bytes to deserialize

        Notes
        -----
        The actual deserialization should be done using the SerializableFactory and its method
        :meth:SerializableFactory.get_apply_deserializer
        """
        ...


# List of all objects serializable via the serializer
SERIALIZABLE = Union[None, bytes, str, int, float, complex, list, tuple, dict, NDArray, SerializableBase]

Serializable = TypeVar("Serializable", bound=SERIALIZABLE)
_SerializableClass = TypeVar("_SerializableClass", bound=SerializableBase)

Serializer = Callable[[Serializable], bytes]
Deserializer = Callable[[bytes], Tuple[Serializable, bytes]]


class SerializableFactory:
    """The factory class for creating executors"""

    serializable_registry: dict[type[SERIALIZABLE], dict[str, Union[Serializer, Deserializer]]] = {}

    @classmethod
    def add_type_to_serialize(
        cls, serialize_method: Callable[[Serializable], bytes]
    ) -> Callable[[Serializable], bytes]:
        def wrap(obj: Serializable) -> bytes:
            bytes_str = b''
            type_as_bytes, len_as_bytes = utils.str_len_to_bytes(obj.__class__.__name__)
            bytes_str += len_as_bytes
            bytes_str += type_as_bytes
            bytes_str += serialize_method(obj)
            return bytes_str
        return wrap

    @classmethod
    def register_from_obj(cls, obj: Serializable, serialize_method: Serializer[Serializable],
                          deserialize_method: Optional[Deserializer[Serializable]] = None):
        """Method to register a serializable object class to the internal registry.

        """
        obj_type = obj.__class__

        cls.register_from_type(
            obj_type=obj_type,
            serialize_method=serialize_method,
            deserialize_method=deserialize_method,
        )

    @classmethod
    def register_decorator(cls) -> Callable[[type[_SerializableClass]], type[_SerializableClass]]:
        """Class decorator method to register exporter class to the internal registry. Must be used as
        decorator above the definition of a SerializableBase inherited class.

        This class must implement specific class methods in particular: serialize and deserialize
        """

        def inner_wrapper(
            wrapped_class: type[_SerializableClass],
        ) -> type[_SerializableClass]:
            cls.register_from_type(wrapped_class,
                                   wrapped_class.serialize,
                                   wrapped_class.deserialize)

            # Return wrapped_class
            return wrapped_class
        return inner_wrapper

    @classmethod
    def register_from_type(cls, obj_type: type[Serializable], serialize_method: Serializer[Serializable],
                           deserialize_method: Deserializer[Serializable]):
        """Method to register a serializable object class to the internal registry.

        """
        if obj_type not in cls.serializable_registry:
            cls.serializable_registry[obj_type] = dict(
                serializer=cls.add_type_to_serialize(serialize_method),
                deserializer=deserialize_method)

    def get_type_from_str(self, obj_type_str: str) -> type:
        for k in self.serializable_registry:
            if obj_type_str in str(k):
                return k
        raise ValueError(f"Unknown type '{obj_type_str}'")

    def get_serializables(self) -> List[type]:
        return list(self.serializable_registry.keys())

    def get_serializer(self, obj_type: type) -> Serializer:
        entry_dict = self.serializable_registry.get(obj_type, None)
        if entry_dict is not None:
            return entry_dict['serializer']  # type: ignore
        else:
            raise NotImplementedError(f"There is no known method to serialize '{obj_type}'")

    def get_apply_serializer(self, obj: SERIALIZABLE, append_length=False) -> bytes:
        """

        Parameters
        ----------
        obj: object
            should be a serializable object (see get_serializables)
        append_length: bool
            if True will append the length of the bytes string in the beginning of the returned
            bytes

        Returns
        -------
        bytes: the encoded object

        Notes
        -----
        Symmetric method of :meth:SerializableFactory.get_apply_deserializer

        Examples
        --------
        >>> ser_factory = SerializableFactory()
        >>> s = [23, 'a']
        >>>> ser_factory.get_apply_deserializer(ser_factory.get_apply_serializer(s) == s
        """
        serializer = self.get_serializer(obj.__class__)
        bytes_str = serializer(obj)
        if not append_length:
            return bytes_str
        else:
            bytes_str = utils.int_to_bytes(len(bytes_str)) + bytes_str
            return bytes_str

    def get_deserializer(self, obj_type: type[Serializable]) -> Deserializer[Serializable]:
        entry_dict = self.serializable_registry.get(obj_type, None)
        if entry_dict is not None:
            return entry_dict['deserializer']  # type: ignore
        else:
            raise NotImplementedError(f"There is no known method to deserialize an '{obj_type}' type")

    def get_apply_deserializer(
        self, bytes_str: bytes, only_object: bool = True
    ) -> Union[SERIALIZABLE, Tuple[SERIALIZABLE, bytes]]:
        """ Infer which object is to be deserialized from the first bytes

        The type has been encoded by the get_apply_serializer method

        Parameters
        ----------
        bytes_str: bytes
            The bytes to convert back to an object
        only_object: bool (default False)
            if False, return the object and the remaining bytes if any
            if True return only the object

        Returns
        -------
        object: the reconstructed object
        optional bytes: only if only_object parameter is False, will be the leftover bytes

        Notes
        -----
        Symmetric method of :meth:SerializableFactory.get_apply_serializer

        Examples
        --------
        >>> ser_factory = SerializableFactory()
        >>> s = [23, 'a']
        >>>> ser_factory.get_apply_deserializer(ser_factory.get_apply_serializer(s) == s
        """
        obj_type_str, remaining_bytes = self.get_deserializer(str)(bytes_str)

        obj_type = self.get_type_from_str(obj_type_str)
        if obj_type is None:
            raise NotImplementedError(f"There is no known method to deserialize an "
                                      f"'{obj_type_str}' type")
        result = self.get_deserializer(obj_type)(remaining_bytes)
        return result[0] if only_object else result
