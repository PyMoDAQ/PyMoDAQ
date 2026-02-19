from concurrent.futures import Future
from typing import Optional

from pymodaq.scripting.utils import Device, LECODashboardWrapper
from pymodaq.utils.data import DataActuator, DataToExport




class Actuator(Device):
    """
    Public interface to control an Actuator
    """
    def get_actuator_value(self) -> Future[DataActuator]:
        return self._leco_device_wrapper.get_actuator_value()

    def move_home(self) -> Future[DataActuator]:
        return self._leco_device_wrapper.move_home()

    def move_abs(self, value: DataActuator | int | float | str ) -> Future[DataActuator]:
        return self._leco_device_wrapper.move_abs(value)

    def move_rel(self, value: DataActuator | int | float | str ) -> Future[DataActuator]:
        return self._leco_device_wrapper.move_rel(value)

    def stop_move(self) -> Future[DataActuator]:
        return self._leco_device_wrapper.stop_move()

class Detector(Device):
    """
    Public interface to control a Detector
    """
    def snap(self) -> Optional[Future[DataToExport]]:
        return self._leco_device_wrapper.snap()

    def grab(self, keep=False) -> Optional[list[DataToExport]]:
        return self._leco_device_wrapper.grab(keep=keep)

    def stop_grab(self) -> None:
       return self._leco_device_wrapper.stop_grab()



class Dashboard:
    """
    Public interface to control a Dashboard
    """

    def __init__(self, **kwargs) -> None:
        self._leco_device_wrapper = LECODashboardWrapper(**kwargs)

    @property
    def leco_name(self):
        return self._leco_device_wrapper.leco_name

    @property
    def name(self) -> str:
        return self._leco_device_wrapper.name


    def sign_out(self) -> None:
        self._leco_device_wrapper.sign_out()

    def get_devices(self) -> Future[dict[str, list[str]]]:
        return self._leco_device_wrapper.get_devices()

    def get_scripting_devices(self) -> dict[str, dict[str, Actuator | Detector]]:
        devices = self._leco_device_wrapper.get_devices().result()

        return {
            'actuators': { name : Actuator(name) for name in devices['actuators']},
            'detectors': { name : Detector(name) for name in devices['detectors']}
        }

    def get_configurations(self) -> Future[list[str]]:
        return self._leco_device_wrapper.get_configurations()

    def apply_configuration(self, configuration : str) -> Future[bool]:
        return self._leco_device_wrapper.apply_configuration(configuration)

    def get_presets(self) -> Future[list[str]]:
        return self._leco_device_wrapper.get_presets()

    def apply_preset(self, preset: str) -> Future[bool]:
        return self._leco_device_wrapper.apply_preset(preset)
