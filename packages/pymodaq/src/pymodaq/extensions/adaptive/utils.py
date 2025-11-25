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

    def __init__(self, ini_random: int, bounds: OrderedDict[str, tuple[float, float]],
                 actuators: list[str],
                 loss_type: LossDim, kind: str, **kwargs):
        super().__init__(ini_random, bounds, actuators)
        self._algo = loss_type.get_learner_from_enum(
            bounds=bounds,
            loss_function=LossFunctionFactory.create(loss_type, kind, **kwargs))
        self._best = 1

    def get_random_point(self) -> dict[str, float]:
        """ Get a random point coordinates in the defined bounds

        Normally not needed for Adaptive
        """
        point = dict()
        bounds = self.bounds
        for ind in range(len(bounds)):
            point[self.actuators[ind]] = ((np.max(bounds[ind]) - np.min(bounds[ind])) * np.random.random_sample() +
                                          np.min(bounds[ind]))
        return point

    def set_prediction_function(self, loss_type=LossDim.LOSS_1D, kind='',  **kwargs):
        self._prediction = LossFunctionFactory.create(loss_type, kind, **kwargs)

    def update_prediction_function(self):
        pass

    @property
    def tradeoff(self) -> float:
        return 0.

    @property
    def bounds(self) -> Dict[str, Tuple[float, float]]:
        return dict(zip(self.actuators, self._algo.bounds))

    @bounds.setter
    def bounds(self, bounds: Dict[str, Tuple[float, float]]):
        if isinstance(bounds, dict):
            bounds = [bounds[act] for act in self.actuators]
            self._algo.set_bounds(bounds)
        else:
            raise TypeError('Bounds should be defined as a dictionary')

    def prediction_ask(self) -> dict[str, float]:
        """ Ask the prediction function or algo to provide the next point to probe"""
        return dict(zip(self.actuators, np.atleast_1d(self._algo.ask(1)[0][0])))

    def tell(self, function_value: float):

        next_point = tuple([self._next_point[act] for act in self.actuators])
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
    def best_individual(self) -> Union[dict[str, float], None]:
        """ Return the individual coordinates with best fitness"""

        if len(self._algo.data) > 0:
            individual_array =  np.atleast_1d(list(self._algo.data.keys())[list(self._algo.data.values()).index(max(self._algo.data.values()))])
        else:
            individual_array =  np.atleast_1d(self._algo.bounds[0])
        return dict(zip(self.actuators, individual_array))

    def best_individuals(self, n_best):
        if len(self._algo.data) > n_best:
            individual_array =  np.atleast_1d(list(self._algo.data.keys())[list(self._algo.data.values()).index(max(self._algo.data.values()))])
        else:
            individual_array =  np.atleast_1d(self._algo.bounds[0])
        return dict(zip(self.actuators, individual_array))


    def stopping(self, ind_iter: int, stopping_parameters: StoppingParameters):
        if stopping_parameters.stop_type != StopType.NONE:
            if ind_iter >= stopping_parameters.niter:  # For instance StopType.ITER
                return True
        return False






