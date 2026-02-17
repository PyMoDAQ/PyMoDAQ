from concurrent.futures import Future
from typing import Optional

from pymodaq.scripting.utils import Device
from pymodaq.utils.data import DataActuator, DataToExport



class Actuator(Device):
    """
    Public interface to control an Actuator
    """
    def get_actuator_value(self) -> Future[DataActuator]:
        return self._leco_wrapper.get_actuator_value()

    def move_home(self) -> Future[DataActuator]:
        return self._leco_wrapper.move_home()

    def move_abs(self, value: DataActuator | int | float | str ) -> Future[DataActuator]:
        return self._leco_wrapper.move_abs(value)

    def move_rel(self, value: DataActuator | int | float | str ) -> Future[DataActuator]:
        return self._leco_wrapper.move_rel(value)

    def stop_move(self) -> Future[DataActuator]:
        return self._leco_wrapper.stop_move()

class Detector(Device):
    """
    Public interface to control a Detector
    """
    def snap(self) -> Optional[Future[DataToExport]]:
        return self._leco_wrapper.snap()

    def grab(self, keep=False) -> Optional[list[DataToExport]]:
        return self._leco_wrapper.grab(keep=keep)

    def stop_grab(self) -> None:
       return self._leco_wrapper.stop_grab()


