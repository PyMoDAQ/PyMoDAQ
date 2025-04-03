# -*- coding: utf-8 -*-
"""
Created the 31/08/2023

@author: Sebastien Weber
"""

from typing import List, TYPE_CHECKING, Union, Dict, Tuple, Iterable

import numpy as np
from collections import OrderedDict
from collections.abc import Iterable as IterableClass


from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq_data.data import (DataCalculated, DataRaw, Axis)


from pymodaq.extensions.optimizers_base.utils import (
    GenericAlgorithm, OptimizerModelDefault, StopType, StoppingParameters,
    OptimizerConfig)
from pymodaq.extensions.adaptive.loss_function.loss_factory import LossDim, LossFunctionBase, LossFunctionFactory

logger = set_logger(get_module_name(__file__))


class AdaptiveConfig(OptimizerConfig):
    config_name = f"adaptive_settings"


class AdaptiveAlgorithm(GenericAlgorithm):

    def __init__(self, ini_random: int, bounds: list[tuple[float, float]],
                 loss_type: LossDim, kind: str, **kwargs):
        super().__init__(ini_random)
        self._algo = loss_type.get_learner_from_enum(
            bounds=bounds,
            loss_function=LossFunctionFactory.create(loss_type, kind, **kwargs))
        self._best = 1

    def set_prediction_function(self, loss_type=LossDim.LOSS_1D, kind='',  **kwargs):
        self._prediction = LossFunctionFactory.create(loss_type, kind, **kwargs)

    def update_prediction_function(self):
        pass

    @property
    def tradeoff(self) -> float:
        return 0.

    @property
    def bounds(self) -> List[np.ndarray]:
        return [np.array(bound) if isinstance(bound, IterableClass) else np.array([bound]) for bound in self._algo.bounds]

    @bounds.setter
    def bounds(self, bounds: Union[Tuple[float, float], Iterable[np.ndarray]]):
        #todo check the type
        self._algo.bounds = bounds

    def prediction_ask(self) -> np.ndarray:
        """ Ask the prediction function or algo to provide the next point to probe"""
        return np.atleast_1d(self._algo.ask(1)[0][0])

    def tell(self, function_value: float):
        next_point = tuple(self._next_point)
        if len(next_point) == 1:
            next_point = next_point[0]  #Learner don't have the same tell method signature
        self._algo.tell(next_point, function_value)
        
    @property
    def best_fitness(self) -> float:
        """ For adaptive optimization this is only used as a stopping critter"""
        if 1/self._algo.loss() > self._best:
            self._best = 1/self._algo.loss()
        return self._best

    @property
    def best_individual(self) -> Union[np.ndarray, None]:
        """ For adaptive optimization this doesn't mean anything"""
        return np.atleast_1d(self.bounds[0])

    def stopping(self, ind_iter: int, stopping_parameters: StoppingParameters):
        if ind_iter >= stopping_parameters.niter:
            return True
        if ind_iter > stopping_parameters.npoints and stopping_parameters.stop_type == 'Predict':
            try:
                return self.best_fitness < stopping_parameters.tolerance
            except IndexError:
                return False
        return False






