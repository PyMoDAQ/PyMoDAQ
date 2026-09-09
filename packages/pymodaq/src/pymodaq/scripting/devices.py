from concurrent.futures import Future
from typing import Optional
from xml.etree.ElementTree import Element

from pymodaq.scripting.utils import (
    Device,
    LECOActuatorWrapper,
    LECODetectorWrapper,
    LECODashboardWrapper,
)
from pymodaq.utils.data import DataActuator, DataToExport




class Actuator(Device[LECOActuatorWrapper]):
    """
    Public interface to control an Actuator
    """
    def __init__(self, device: str, **kwargs) -> None:
        super().__init__(LECOActuatorWrapper(device, **kwargs))

    def get_actuator_value(self) -> Future[DataActuator]:
        return self._wrapper.get_actuator_value()

    def move_home(self) -> Future[DataActuator]:
        return self._wrapper.move_home()

    def move_abs(self, value: DataActuator | int | float | str) -> Future[DataActuator]:
        return self._wrapper.move_abs(value)

    def move_rel(self, value: DataActuator | int | float | str) -> Future[DataActuator]:
        return self._wrapper.move_rel(value)

    def stop_move(self) -> Future[DataActuator]:
        return self._wrapper.stop_move()

    def get_settings(self) -> Future[Element]:
        return self._wrapper.get_settings()

    def set_settings(self, settings: Element) -> None:
        self._wrapper.set_settings(settings)

class Detector(Device[LECODetectorWrapper]):
    """
    Public interface to control a Detector
    """
    def __init__(self, device: str, **kwargs) -> None:
        super().__init__(LECODetectorWrapper(device, **kwargs))

    def snap(self) -> Optional[Future[DataToExport]]:
        return self._wrapper.snap()

    def grab(self, keep=False) -> Optional[list[DataToExport]]:
        return self._wrapper.grab(keep=keep)

    def stop_grab(self) -> None:
        return self._wrapper.stop_grab()

    def get_settings(self) -> Future[Element]:
        return self._wrapper.get_settings()

    def set_settings(self, settings: Element) -> None:
        self._wrapper.set_settings(settings)

class Dashboard(Device[LECODashboardWrapper]):
    """
    Public interface to control a Dashboard
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(LECODashboardWrapper(**kwargs))

    @property
    def leco_name(self):
        return self._wrapper.leco_name

    @property
    def name(self) -> str:
        return self._wrapper.name

    def sign_out(self) -> None:
        self._wrapper.sign_out()

    def get_devices(self) -> Future[dict[str, list[str]]]:
        return self._wrapper.get_devices()

    def get_scripting_devices(self) -> dict[str, dict[str, Actuator | Detector]]:
        devices = self._wrapper.get_devices().result()

        return {
            'actuators': {name: Actuator(name) for name in devices['actuators']},
            'detectors': {name: Detector(name) for name in devices['detectors']},
        }

    def get_states(self) -> Future[list[str]]:
        return self._wrapper.get_states()

    def apply_state(self, state: str) -> Future[bool]:
        return self._wrapper.apply_state(state)

    def get_experiments(self) -> Future[list[str]]:
        return self._wrapper.get_experiments()

    def apply_experiment(self, experiment: str) -> Future[bool]:
        return self._wrapper.apply_experiment(experiment)