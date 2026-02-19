import atexit
import xml.etree.ElementTree as ET
from abc import ABC

from concurrent.futures import Future, InvalidStateError
from functools import cached_property
from typing import Optional, cast
from xml.etree.ElementTree import Element

from pyleco.directors.director import Director
from pyleco.utils.listener import Listener
from serializall import SerializableFactory, utils

from pymodaq import Q_
from pymodaq.utils.data import DataActuator, DataToExport



sf = SerializableFactory()

def compare_xml_trees(base: Element, modified: Element) -> list[tuple[list[str], bytes]]:
    """
    Compare two XML trees and return changes.

    Returns:
        list of tuples: (path_list, changed_element_bytes)
    """

    changes = []

    def compare_elements(base_elem, modified_elem, path):
        """Recursively compare elements"""
        # Compare text content (strip whitespace)
        text1 = (base_elem.text or '').strip()
        text2 = (modified_elem.text or '').strip()

        if text1 != text2:
            # Text changed - record this element
            changed_bytes = ET.tostring(modified_elem)
            changes.append((path.copy(), changed_bytes))
            return  # Don't recurse further into this branch

        # Compare attributes (optional - if you want to detect attribute changes)
        if base_elem.attrib != modified_elem.attrib:
            changed_bytes = ET.tostring(modified_elem)
            changes.append((path.copy(), changed_bytes))
            return

        # Compare children
        children1 = list(base_elem)
        children2 = list(modified_elem)

        # Build tag-to-element mapping
        children1_dict = {child.tag: child for child in children1}
        children2_dict = {child.tag: child for child in children2}

        # Recursively compare matching children
        for tag in children1_dict.keys():
            if tag in children2_dict:
                compare_elements(children1_dict[tag], children2_dict[tag],
                                 path + [tag])

    # Start comparison with forced prefix: ['detector_settings', 'settings_client']
    initial_path = [base.tag or modified.tag]
    compare_elements(base, modified, initial_path)

    return changes


def value_to_data_actuator(value: DataActuator | int | float | str) -> DataActuator:
    """
    Converts any kind of convertible value into a DataActuator
    Parameters
    ----------
    value: The value to convert

    Returns
    -------
    A DataActuator object containing the value
    """
    if any(isinstance(value, t) for t in (int, float)):
        return DataActuator(data=value)
    if isinstance(value, str):
        value = Q_(value)
    if isinstance(value, Q_):
        return DataActuator(data=value.magnitude, units=str(value.units))
    return value


class Device(ABC):
    def __init__(self, device, **kwargs) -> None:
        self._leco_device_wrapper = LECODeviceWrapper(device, **kwargs)

    @property
    def leco_name(self):
        return self._leco_device_wrapper.leco_name

    @property
    def name(self) -> str:
        return self._leco_device_wrapper.name

    def get_settings(self) -> Future[Element]:
        return self._leco_device_wrapper.get_settings()

    def set_settings(self, settings: Element) -> None:
        self._leco_device_wrapper.set_settings(settings)

    def sign_out(self) -> None:
        self._leco_device_wrapper.sign_out()



class LECODeviceWrapper:
    """
    Private LECOWrapper where the real control happens
    """
    def __init__(self, device , **kwargs) -> None:
        self._base_settings : Optional[Element] = None

        self._settings_future : Optional[Future[Element]] = None
        self._snap_data_future : Optional[Future[DataToExport]] = None
        self._send_position_future: Optional[Future[DataActuator]] = None
        self._move_done_future: Optional[Future[DataActuator]] = None

        self._grab_data_list : Optional[list[DataToExport]] = None

        self._is_grabbing = False

        self._device_name: str = device
        self._listener = Listener(name=self.leco_name, timeout=None)
        self._listener.start_listen()

        self._listener.register_rpc_method(self.set_director_settings)
        self._listener.register_binary_rpc_method(self.set_data, accept_binary_input=True)
        self._listener.register_binary_rpc_method(self.send_position, accept_binary_input=True)
        self._listener.register_binary_rpc_method(self.set_move_done, accept_binary_input=True)
        self._listener.register_binary_rpc_method(self.set_director_info, accept_binary_input=True)

        self._communicator = self._listener.get_communicator()
        self._director = Director(actor=self.name, communicator=self._communicator, **kwargs)
        atexit.register(self.clean)


    @cached_property
    def leco_name(self):
        return f'scripting_{self.name}'

    @cached_property
    def name(self):
        return self._device_name

    def clean(self):
        self.sign_out()
        self._listener.close()
        self._director.close()
        self._communicator.close()


    def set_remote_name(self):
        self._director.ask_rpc('set_remote_name', name=self.leco_name)

    def get_settings(self) -> Future[Element]:
        future = Future()
        self._settings_future = future

        self.set_remote_name()
        self._director.ask_rpc(method="get_settings")

        return future

    def set_settings(self, settings: Element):
        if self._base_settings is not None:
            for (path, modified) in compare_xml_trees(self._base_settings, settings):
                t_name, t_len = utils.str_len_to_bytes('ParameterWithPath')
                data =  t_len + t_name + sf.get_apply_serializer(path) + sf.get_apply_serializer(modified)
                self._director.ask_rpc(method="set_info", parameter=None, additional_payload=[data])

    def sign_out(self):
        self._director.ask_rpc('sign_out', actor='COORDINATOR')



    def snap(self) -> Optional[Future[DataToExport]]:
        if not self._is_grabbing:
            future = Future()
            self._snap_data_future = future
            self.set_remote_name()
            self._director.ask_rpc(method="send_data_snap")
            return future
        return None



    def grab(self, keep=False) -> Optional[list[DataToExport]]:
        was_grabbing = self._is_grabbing

        if not was_grabbing:
            self._grab_data_list = [] if keep else None

        self.set_remote_name()
        self._director.ask_rpc(method="send_data_grab")
        self._is_grabbing = not was_grabbing

        return None if was_grabbing else self._grab_data_list

    def stop_grab(self):
        self._is_grabbing = False
        self.set_remote_name()
        self._director.ask_rpc(method="stop_grab")



    def get_actuator_value(self) -> Future[DataActuator]:
        future = Future()
        self._send_position_future = future

        self.set_remote_name()
        self._director.ask_rpc('get_actuator_value')

        return future

    def move_home(self) -> Future[DataActuator]:
        future = Future()
        self._move_done_future = future

        self.set_remote_name()
        self._director.ask_rpc(method="move_home")

        return future

    def move_abs(self, value: DataActuator | int | float | str ) -> Future[DataActuator]:
        future = Future()
        self._move_done_future = future

        value = value_to_data_actuator(value)
        serialize = SerializableFactory().get_apply_serializer

        self.set_remote_name()
        self._director.ask_rpc(method="move_abs", position=None, additional_payload=[serialize(value)])

        return future

    def move_rel(self, value: DataActuator) -> Future[DataActuator]:
        future = Future()
        self._move_done_future = future

        value = value_to_data_actuator(value)
        serialize = SerializableFactory().get_apply_serializer

        self.set_remote_name()
        self._director.ask_rpc(method="move_rel", position=None, additional_payload=[serialize(value)])

        return future

    def stop_move(self) -> Future[DataActuator]:
        future = Future()
        self._move_done_future = future

        self.set_remote_name()
        self._director.ask_rpc(method="stop_motion")

        return future


    def set_director_settings(self, settings : bytes):
        # Important to have two creations so they can be compared
        # for modifications later.
        self._base_settings = ET.fromstring(settings)
        try:
            self._settings_future.set_result(ET.fromstring(settings))
            self._settings_future = None
        except (InvalidStateError, AttributeError):
            pass


    def set_data(self, data = None, additional_payload = None):
        value : DataToExport = cast(DataToExport, sf.get_apply_deserializer(additional_payload[0]))
        if self._is_grabbing:
            if self._grab_data_list is not None:
                self._grab_data_list.append(value)
        else:
            try:
                self._snap_data_future.set_result(value)
                self._snap_data_future = None
            except (InvalidStateError, AttributeError):
                pass



    def send_position(self, data = None, additional_payload = None):
        value : DataActuator = cast(DataActuator, sf.get_apply_deserializer(additional_payload[0]))
        try:
            self._send_position_future.set_result(value)
            self._send_position_future = None
        except (InvalidStateError, AttributeError):
            pass

    def set_move_done(self, data = None, additional_payload = None):
        value : DataActuator = cast(DataActuator, sf.get_apply_deserializer(additional_payload[0]))
        try:
            self._move_done_future.set_result(value)
            self._move_done_future = None
        except (InvalidStateError, AttributeError):
            pass

    def set_director_info(self, parameter = None, additional_payload = None) -> None:
        pass


class LECODashboardWrapper:
    def __init__(self, **kwargs) -> None:
        self._presets_future: Optional[Future[list[str]]] = None
        self._applied_preset_future: Optional[Future[bool]] = None
        self._configurations_future: Optional[Future[list[str]]] = None
        self._applied_configuration_future: Optional[Future[bool]] = None
        self._devices_list_future: Optional[Future[dict[str, list[str]]]] = None
        self._device_name: str = 'dashboard'
        self._listener = Listener(name=self.leco_name, timeout=None)
        self._listener.start_listen()

        self._listener.register_binary_rpc_method(self.send_devices, accept_binary_input=True)
        self._listener.register_rpc_method(self.send_configurations)
        self._listener.register_rpc_method(self.send_presets)
        self._listener.register_rpc_method(self.applied_preset_done)
        self._listener.register_rpc_method(self.applied_configuration_done)

        self._communicator = self._listener.get_communicator()
        self._director = Director(actor=self.name, communicator=self._communicator, **kwargs)
        atexit.register(self.clean)


    @cached_property
    def leco_name(self):
        return f'scripting_{self.name}'

    @cached_property
    def name(self):
        return self._device_name

    def clean(self):
        self.sign_out()
        self._listener.close()
        self._director.close()
        self._communicator.close()

    def sign_out(self):
        self._director.ask_rpc('sign_out', actor='COORDINATOR')

    def set_remote_name(self):
        self._director.ask_rpc('set_remote_name', name=self.leco_name)

    def get_devices(self) -> Future[dict[str, list[str]]]:
        future = Future()
        self._devices_list_future = future

        self.set_remote_name()
        self._director.ask_rpc(method="get_devices")

        return future

    def get_configurations(self) -> Future[list[str]]:
        future = Future()
        self._configurations_future = future

        self.set_remote_name()
        self._director.ask_rpc(method="get_configurations")

        return future

    def apply_configuration(self, configuration: str) -> Future[bool]:
        future = Future()
        self._applied_configuration_future = future

        self.set_remote_name()
        self._director.ask_rpc(method="apply_configuration", configuration=configuration)

        return future

    def get_presets(self) -> Future[list[str]]:
        future = Future()
        self._presets_future = future

        self.set_remote_name()
        self._director.ask_rpc(method="get_presets")

        return future

    def apply_preset(self, preset : str) -> Future[bool]:
        future = Future()
        self._applied_preset_future = future

        self.set_remote_name()
        self._director.ask_rpc(method="apply_preset", preset=preset)

        return future

    def send_devices(self, data = None, additional_payload = None):
        value: dict[str, list[str]] = sf.get_apply_deserializer(additional_payload[0])
        try:
            self._devices_list_future.set_result(value)
            self._devices_list_future = None
        except (InvalidStateError, AttributeError):
            pass

    def send_configurations(self, configurations: list[str]):
        try:
            self._configurations_future.set_result(configurations)
            self._configurations_future = None
        except (InvalidStateError, AttributeError):
            pass

    def send_presets(self, presets: list[str]):
        try:
            self._presets_future.set_result(presets)
            self._presets_future = None
        except (InvalidStateError, AttributeError):
            pass

    def applied_preset_done(self, done: bool):
        try:
            self._applied_preset_future.set_result(done)
            self._applied_preset_future = None
        except (InvalidStateError, AttributeError):
            pass

    def applied_configuration_done(self, done: bool):
        try:
            self._applied_configuration_future.set_result(done)
            self._applied_configuration_future = None
        except (InvalidStateError, AttributeError):
            pass
