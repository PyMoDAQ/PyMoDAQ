from dataclasses import dataclass
from typing import Union, Tuple


from pymodaq.utils.managers.modules_manager import ModuleType
from pymodaq_gui.parameter.utils import ParameterWithPath
from pymodaq_utils import SerializableFactory

ser_factory = SerializableFactory()


@SerializableFactory.register_decorator()
@dataclass
class ConfiguratorEntry:
    entry_type: str
    module_name: str
    module_type: ModuleType
    setting: ParameterWithPath

    def __eq__(self, other: 'ConfiguratorEntry'):
        return (self.entry_type == other.entry_type and
                self.module_name == other.module_name and
                self.module_type == other.module_type and
                self.setting == other.setting)

    def __repr__(self):
        return f"ConfiguratorEntry({self.entry_type} for {self.module_type} module {self.module_name}:"\
               f" {self.setting.value()}"

    @staticmethod
    def serialize(entry: 'ConfiguratorEntry') -> bytes:
        """

        """
        bytes_string = b''
        bytes_string += ser_factory.get_apply_serializer(entry.entry_type)
        bytes_string += ser_factory.get_apply_serializer(entry.setting)
        bytes_string += ser_factory.get_apply_serializer(entry.module_name)
        bytes_string += ser_factory.get_apply_serializer(entry.module_type.value)
        return bytes_string

    @classmethod
    def deserialize(cls,
                    bytes_str: bytes) -> Union['ConfiguratorEntry',
    Tuple['ConfiguratorEntry', bytes]]:
        """Convert bytes into a ParameterWithPath object

        Returns
        -------
        ParameterWithPath: the decoded object
        bytes: the remaining bytes string if any
        """
        entry_type , remaining_bytes = ser_factory.get_apply_deserializer(bytes_str, False)
        parameter_with_path, remaining_bytes = ser_factory.get_apply_deserializer(remaining_bytes, False)
        module_name, remaining_bytes = ser_factory.get_apply_deserializer(remaining_bytes, False)
        module_type, remaining_bytes = ser_factory.get_apply_deserializer(remaining_bytes, False)
        return ConfiguratorEntry(entry_type,
                                 module_name,
                                 ModuleType(module_type),
                                 parameter_with_path), remaining_bytes
