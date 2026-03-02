import abc
from collections import OrderedDict
from typing import Optional, Union

from pymodaq.extensions.optimizers_base.utils import PredictionError, StoppingParameters
from pymodaq_utils.abstract import abstract_attribute


class GenericAlgorithm(abc.ABC):

    def __init__(self, ini_random: int, bounds: OrderedDict[str, tuple[float, float]], actuators: list[str]):

        self._algo = abstract_attribute()  #could be a Bayesian on Adaptive algorithm
        self._prediction = abstract_attribute()  # could be an acquisition function...

        self.actuators = actuators
        self.ini_bounds = bounds

        self._next_point: Optional[dict[str, float]] = None
        self._suggested_coordinates: list[dict[str, float]]  = []
        self.ini_random_points = ini_random

    @abc.abstractmethod
    def set_prediction_function(self, kind: str='', **kwargs):
        """ Set/Load a given function/class to predict next probed points"""

    @abc.abstractmethod
    def update_prediction_function(self):
        """ Update the parameters of the prediction function (kappa decay for instance)"""

    def set_acquisition_function(self, kind: str, **kwargs):
        """ Deprecated"""
        self.set_prediction_function(kind, **kwargs)

    def update_acquisition_function(self):
        """ deprecated"""
        self.update_prediction_function()

    @property
    def _acquisition(self):
        """ deprecated """
        return self._prediction

    @property
    def tradeoff(self):
        return self._prediction.tradeoff

    @property
    @abc.abstractmethod
    def bounds(self) -> dict[str, tuple[float, float]]:
        ...

    @bounds.setter
    def bounds(self, bounds: dict[str, tuple[float, float]]):
        ...

    @abc.abstractmethod
    def get_random_point(self) -> dict[str, float]:
        """ Get a random point coordinates in the defined bounds"""
        ...

    def ask(self) -> dict[str, float]:
        """ Predict next actuator values to probe

        Return a DataToActuator, one DataWithAxes per actuator. In general these dwa are 0D
        """
        try:
            self._next_point = self.prediction_ask()
        except PredictionError:
            self.ini_random_points -= 1
            self._next_point = self.get_random_point()
        self._suggested_coordinates.append(self._next_point)
        return self._next_point

    @abc.abstractmethod
    def prediction_ask(self) -> dict[str, float]:
        """ Ask the prediction function or algo to provide the next point to probe"""

    @abc.abstractmethod
    def tell(self, function_value: float):
        """ Add next points and function value into the algo"""

    @property
    @abc.abstractmethod
    def best_fitness(self) -> float:
        pass

    @property
    @abc.abstractmethod
    def best_individual(self) -> Union[dict[str, float], None]:
        pass

    @abc.abstractmethod
    def stopping(self, ind_iter: int, stopping_parameters: StoppingParameters) -> bool:
        pass
