# -*- coding: utf-8 -*-
"""
Created the 31/08/2023

@author: Sebastien Weber
"""

from typing import List, TYPE_CHECKING, Union, Dict, Tuple, Iterable

import bayes_opt.exception
import numpy as np
from collections import namedtuple

from bayes_opt import BayesianOptimization
from bayes_opt.exception import TargetSpaceEmptyError


from pymodaq_utils.logger import set_logger, get_module_name


from pymodaq_data.data import (DataToExport, DataCalculated,
                                DataRaw, Axis)


from pymodaq.extensions.bayesian.acquisition import GenericAcquisitionFunctionFactory

from pymodaq.extensions.optimizers_base.utils import (
    GenericAlgorithm, OptimizerModelDefault, StopType, StoppingParameters,
    OptimizerConfig, PredictionError)


logger = set_logger(get_module_name(__file__))


class BayesianConfig(OptimizerConfig):
    config_name = f"bayesian_settings"



class BayesianAlgorithm(GenericAlgorithm):

    def __init__(self, ini_random: int, bounds: dict[str, tuple[float, float]], actuators: list[str], **kwargs):
        super().__init__(ini_random, bounds, actuators)
        self._algo = BayesianOptimization(f=None,
                                          pbounds=bounds,
                                          **kwargs
                                          )
        self.sorting_index: list = None

    def set_prediction_function(self, kind: str = '', **kwargs):
        self._prediction = GenericAcquisitionFunctionFactory.create(kind, **kwargs)

    def update_prediction_function(self):
        """ Update the parameters of the acquisition function (kappa decay for instance)"""
        self._prediction.decay_exploration()

    @property
    def tradeoff(self):
        return self._prediction.tradeoff

    def get_random_point(self) -> dict[str, float]:
        """ Get a random point coordinates in the defined bounds"""
        point = dict()
        for key, vals in self.bounds.items():
            point[key] = (np.max(vals) - np.min(vals)) * np.random.random_sample() + np.min(vals)
        return point

    @property
    def bounds(self) -> dict[str, float]:
        """ Return bounds as a dict.
        """
        return self._algo.space.array_to_params(self._algo.space.bounds)

    @bounds.setter
    def bounds(self, bounds: Dict[str, Tuple[float, float]]):
        if isinstance(bounds, dict):
            self._algo.set_bounds(bounds)
        else:
            raise TypeError('Bounds should be defined as a dictionary')

    def prediction_ask(self) -> dict[str, float]:
        """ Ask the prediction function or algo to provide the next point to probe

        Warning the space algo object is sorting by name the bounds...
        """
        try:
            return self._algo.space.array_to_params(self._prediction.suggest(self._algo._gp, self._algo.space))
        except TargetSpaceEmptyError as e:
            raise PredictionError(str(e))


    def tell(self, function_value: float):
        self._algo.register(params=self._next_point, target=function_value)
        
    @property
    def best_fitness(self) -> float:
        if self._algo.max is None:
            return 0.001
        else:
            return self._algo.max['target']

    @property
    def best_individual(self) -> Union[dict[str, float], None]:
        if self._algo.max is None:
            return None
        else:
            max_param = self._algo.max.get('params', None)
            if max_param is None:
                return None
            return max_param

    def stopping(self, ind_iter: int, stopping_parameters: StoppingParameters):
        if stopping_parameters.stop_type != StopType.NONE:
            if ind_iter >= stopping_parameters.niter:  # For instance StopType.ITER
                return True
            if ind_iter > stopping_parameters.npoints:
                if stopping_parameters.stop_type == StopType.PREDICT:
                    coordinates = np.atleast_1d([
                        [coordinates[act] for coordinates in self._suggested_coordinates[-stopping_parameters.npoints:]]
                        for act in self.actuators])
                    return np.all(np.abs((np.std(coordinates, axis=1) / np.mean(coordinates, axis=1)))
                                  < stopping_parameters.tolerance)
                elif stopping_parameters.stop_type == StopType.BEST:
                    coordinates = np.atleast_1d(
                        [[best['params'][act] for best in
                          sorted(self._algo.res, key=lambda x: x['target'])[-stopping_parameters.npoints:]]
                         for act in self.actuators])
                    return np.all(np.abs((np.std(coordinates, axis=1) / np.mean(coordinates, axis=1)))
                                  < stopping_parameters.tolerance)
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



