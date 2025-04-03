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
        self._algo.tell(x=next_point, y=function_value)
        
    @property
    def best_fitness(self) -> float:
        try:
            return 1 / self._algo.losses.peekitem(-1)[1]
        except (IndexError, ValueError):
            return 1

    @property
    def best_individual(self) -> Union[np.ndarray, None]:
        try:
            return np.atleast_1d(self._algo.losses.peekitem(-1)[0])
        except IndexError:
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

    def _posterior(self, x_obs, y_obs, grid):

        if len(x_obs.shape) == 1:
            x_obs = x_obs.reshape(-1, 1)
            y_obs = y_obs.reshape(-1, 1)
            grid = grid.reshape(-1, 1)

        self._algo._gp.fit(x_obs, y_obs)

        mu, sigma = self._algo._gp.predict(grid, return_std=True)
        return mu, sigma

    def get_dwa_obervations(self, actuators_name):
        try:
            axes = [Axis(act, data=np.array([res['params'][act] for res in self._algo.res])) for
                    act in actuators_name]
            data_arrays = [np.array([res['target'] for res in self._algo.res])]

            return DataRaw('Observations', data=data_arrays, labels=actuators_name,
                           axes=axes)

        except Exception as e:
            pass

    def get_1D_dwa_gp(self, x: np.ndarray, actuator_name: str):
        """ Get Measurements and predictions as DataWithAxes

        Parameters
        ----------
        x: np.ndarray
            linear grid to get the Bayesian Optimisation On
        """

        dwa_obervation = self.get_dwa_obervations([actuator_name])

        mu, sigma = self._posterior(dwa_obervation.axes[0].get_data(),
                                    dwa_obervation.data[0], x)

        dwa_measured = DataCalculated('Measurements', data=[dwa_obervation.data[0]],
                                      axes=[Axis('measured_axis',
                                                 data=dwa_obervation.axes[0].get_data())],
                                      labels=['Sampled'])
        dwa_prediction = DataCalculated('Prediction', data=[mu],
                                        axes=[Axis('tested_pos', data=x)],
                                        errors=[1.96 * sigma])
        return dwa_measured, dwa_prediction



