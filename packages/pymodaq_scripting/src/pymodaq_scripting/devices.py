from concurrent.futures import Future
from typing import Optional, TYPE_CHECKING, Union
from xml.etree.ElementTree import Element
from pymodaq_data.data import DataToExport
from pymodaq_scripting.utils import (
    Device,
    LECOActuatorWrapper,
    LECODetectorWrapper,
    LECODashboardWrapper,
)

if TYPE_CHECKING:
    from pymodaq.utils.data import DataActuator


class Actuator(Device[LECOActuatorWrapper]):
    """
    Public interface to control an Actuator of a running Dashboard

    All the commands return at once with a :class:`concurrent.futures.Future`, filled when the Dashboard
    answers: call ``result()`` on it to wait for the answer. A new command of the same kind replaces the
    previous one, whose future then never completes (the four moves share the same future).

    Parameters
    ----------
    device: str
        Name of the actuator in the Dashboard (its title in the experiment)
    **kwargs
        Passed to the LECO ``Director`` (for example the ``host`` of the coordinator)

    Examples
    --------
    >>> actuator = Actuator('Xaxis')
    >>> actuator.move_abs('1.5 mm').result()  # position reached, as a DataActuator
    >>> actuator.get_actuator_value().result()
    """
    def __init__(self, device: str, **kwargs) -> None:
        super().__init__(LECOActuatorWrapper(device, **kwargs))

    def get_actuator_value(self) -> Future['DataActuator']:
        """ Ask for the current position of the actuator

        Returns
        -------
        Future: its result is the position, as a ``DataActuator``
        """
        return self._wrapper.get_actuator_value()

    def move_home(self) -> Future['DataActuator']:
        """ Move the actuator to its home position

        Returns
        -------
        Future: its result is the position once the move is over
        """
        return self._wrapper.move_home()

    def move_abs(self, value: Union['DataActuator', int, float, str]) -> Future['DataActuator']:
        """ Move the actuator to an absolute position

        Parameters
        ----------
        value: DataActuator, int, float or str
            The target. A number is sent without units, a string is read with its units (``'1.5 mm'``,
            see :func:`pymodaq_scripting.utils.value_to_data_actuator`).

        Returns
        -------
        Future: its result is the position once the move is over
        """
        return self._wrapper.move_abs(value)

    def move_rel(self, value: Union['DataActuator', int, float, str]) -> Future['DataActuator']:
        """ Move the actuator by a displacement relative to its current position

        Parameters
        ----------
        value: DataActuator, int, float or str
            The displacement, same conversions as in :meth:`move_abs`

        Returns
        -------
        Future: its result is the position once the move is over
        """
        return self._wrapper.move_rel(value)

    def stop_move(self) -> Future['DataActuator']:
        """ Stop the movement of the actuator

        Returns
        -------
        Future: its result is the position once the actuator is stopped
        """
        return self._wrapper.stop_move()

    def get_settings(self) -> Future[Element]:
        """ Ask for the settings of the actuator

        Returns
        -------
        Future: its result is the settings tree, as an XML ``Element``. It is also kept as the reference
        against which :meth:`set_settings` detects what changed.
        """
        return self._wrapper.get_settings()

    def set_settings(self, settings: Element) -> None:
        """ Send the settings that differ from those obtained by the last :meth:`get_settings`

        Only the parameters whose value or attributes changed are sent. Nothing is sent as long as the answer
        to :meth:`get_settings` has not been received.

        Parameters
        ----------
        settings: Element
            The settings tree returned by :meth:`get_settings`, with some values modified
        """
        self._wrapper.set_settings(settings)


class Detector(Device[LECODetectorWrapper]):
    """
    Public interface to control a Detector of a running Dashboard

    Parameters
    ----------
    device: str
        Name of the detector in the Dashboard (its title in the experiment)
    **kwargs
        Passed to the LECO ``Director`` (for example the ``host`` of the coordinator)

    Examples
    --------
    >>> detector = Detector('Camera')
    >>> data = detector.snap().result()  # a DataToExport
    """
    def __init__(self, device: str, **kwargs) -> None:
        super().__init__(LECODetectorWrapper(device, **kwargs))

    def snap(self) -> Optional[Future[DataToExport]]:
        """ Acquire one data set

        Returns
        -------
        Future or None: its result is the acquired ``DataToExport``. None, and nothing is asked, while a
        continuous grab started by :meth:`grab` is running.
        """
        return self._wrapper.snap()

    def grab(self, keep: bool = False) -> Optional[list[DataToExport]]:
        """ Start a continuous acquisition, or stop it when one is running (each call toggles)

        Parameters
        ----------
        keep: bool
            If True, the data sets received while grabbing are appended to the returned list. Only used by
            the call starting the grab.

        Returns
        -------
        list or None: when starting with ``keep=True``, the list filling up with the acquired ``DataToExport``;
        None otherwise (``keep=False``, or the call stopping the grab).
        """
        return self._wrapper.grab(keep=keep)

    def stop_grab(self) -> None:
        """ Stop the continuous acquisition """
        return self._wrapper.stop_grab()

    def get_settings(self) -> Future[Element]:
        """ Ask for the settings of the detector

        Returns
        -------
        Future: its result is the settings tree, as an XML ``Element``. It is also kept as the reference
        against which :meth:`set_settings` detects what changed.
        """
        return self._wrapper.get_settings()

    def set_settings(self, settings: Element) -> None:
        """ Send the settings that differ from those obtained by the last :meth:`get_settings`

        Only the parameters whose value or attributes changed are sent. Nothing is sent as long as the answer
        to :meth:`get_settings` has not been received.

        Parameters
        ----------
        settings: Element
            The settings tree returned by :meth:`get_settings`, with some values modified
        """
        self._wrapper.set_settings(settings)


class Dashboard(Device[LECODashboardWrapper]):
    """
    Public interface to control a Dashboard

    Parameters
    ----------
    **kwargs
        Passed to the LECO ``Director`` (for example the ``host`` of the coordinator)

    Examples
    --------
    >>> dashboard = Dashboard()
    >>> dashboard.apply_experiment('my_experiment').result()  # True once applied
    >>> devices = dashboard.get_scripting_devices()
    >>> devices['actuators']['Xaxis'].move_abs('1 mm').result()
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(LECODashboardWrapper(**kwargs))

    @property
    def leco_name(self) -> str:
        """ Name under which this script is known on the LECO network"""
        return self._wrapper.leco_name

    @property
    def name(self) -> str:
        """ Name of the Dashboard on the LECO network"""
        return self._wrapper.name

    def sign_out(self) -> None:
        """ Sign this script out of the LECO coordinator (done automatically when Python exits)"""
        self._wrapper.sign_out()

    def get_devices(self) -> Future[dict[str, list[str]]]:
        """ Ask for the names of the instruments of the applied experiment

        Returns
        -------
        Future: its result is a dict with the keys ``'actuators'`` and ``'detectors'``, each holding the list
        of the names
        """
        return self._wrapper.get_devices()

    def get_scripting_devices(self) -> dict[str, dict[str, Actuator | Detector]]:
        """ Get an :class:`Actuator` or :class:`Detector` object for each instrument of the experiment

        Waits for the answer of the Dashboard (see :meth:`get_devices`).

        Returns
        -------
        dict: ``{'actuators': {name: Actuator}, 'detectors': {name: Detector}}``
        """
        devices = self._wrapper.get_devices().result()

        return {
            'actuators': {name: Actuator(name) for name in devices['actuators']},
            'detectors': {name: Detector(name) for name in devices['detectors']},
        }

    def get_states(self) -> Future[list[str]]:
        """ Ask for the names of the available states

        Returns
        -------
        Future: its result is the list of names
        """
        return self._wrapper.get_states()

    def apply_state(self, state: str) -> Future[bool]:
        """ Apply a state (instrument settings and actuator values)

        Parameters
        ----------
        state: str
            Name of the state, as returned by :meth:`get_states`

        Returns
        -------
        Future: its result is the success of the operation, set when the state has been applied
        """
        return self._wrapper.apply_state(state)

    def get_experiments(self) -> Future[list[str]]:
        """ Ask for the names of the available experiments

        Returns
        -------
        Future: its result is the list of names
        """
        return self._wrapper.get_experiments()

    def apply_experiment(self, experiment: str) -> Future[bool]:
        """ Load an experiment (the list of instruments the Dashboard manages)

        Parameters
        ----------
        experiment: str
            Name of the experiment, as returned by :meth:`get_experiments`

        Returns
        -------
        Future: its result is the success of the operation, set when the experiment has been applied
        """
        return self._wrapper.apply_experiment(experiment)