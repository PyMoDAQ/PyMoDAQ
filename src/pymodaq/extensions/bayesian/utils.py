# -*- coding: utf-8 -*-
"""
Created the 31/08/2023

@author: Sebastien Weber
"""
from abc import ABC, abstractproperty, abstractmethod
from typing import List, TYPE_CHECKING, Union, Dict, Tuple, Iterable
from pathlib import Path
import importlib
import pkgutil
import inspect
import numpy as np
from collections import namedtuple

from bayes_opt import BayesianOptimization
from bayes_opt import UtilityFunction

from pymodaq_utils.utils import find_dict_in_list_from_key_val, get_entrypoints
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.enums import BaseEnum
from pymodaq_utils.config import BaseConfig

from pymodaq_gui.parameter import Parameter
from pymodaq_gui.plotting.data_viewers.viewer import ViewersEnum

from pymodaq_data.data import (DataToExport, DataCalculated,
                                DataRaw, Axis)

from pymodaq.utils.data import DataActuator, DataToActuators
from pymodaq.utils.managers.modules_manager import ModulesManager


if TYPE_CHECKING:
    from pymodaq.extensions.bayesian.bayesian_optimisation import BayesianOptimisation

logger = set_logger(get_module_name(__file__))


class StopType(BaseEnum):
    Predict = 0


class UtilityKind(BaseEnum):
    ucb = 'Upper Confidence Bound'
    ei = 'Expected Improvement'
    poi = 'Probability of Improvement'


UtilityParameters = namedtuple('UtilityParameters',
                               ['kind', 'kappa', 'xi', 'kappa_decay', 'kappa_decay_delay'])


StoppingParameters = namedtuple('StoppingParameters',
                                ['niter', 'stop_type', 'tolerance', 'npoints'])


class BayesianAlgorithm:

    def __init__(self, ini_random: int, bounds: dict, **kwargs):

        self._algo = BayesianOptimization(f=None,
                                          pbounds=bounds,
                                          **kwargs
                                          )
        self._next_point: np.ndarray = None
        self._suggested_coordinates: List[np.ndarray] = []
        self.ini_random_points = ini_random
        self.kappa = 2.5

        self._utility = UtilityFunction(kind="ucb", kappa=self.kappa, xi=0.0)

    def set_utility_function(self, kind: str, **kwargs):
        if kind in UtilityKind.names():
            self._utility = UtilityFunction(kind, **kwargs)

    def update_utility_function(self):
        """ Update the parameters of the Utility function (kappa decay for instance)"""
        self._utility.update_params()
        self.kappa = self._utility.kappa

    @property
    def bounds(self) -> List[np.ndarray]:
        return [bound for bound in self._algo._space.bounds]

    @bounds.setter
    def bounds(self, bounds: Union[Dict[str, Tuple[float, float]], Iterable[np.ndarray]]):
        if isinstance(bounds, dict):
            self._algo.set_bounds(bounds)
        else:
            self._algo.set_bounds(self._algo._space.array_to_params(np.array(bounds)))

    def get_random_point(self) -> np.ndarray:
        """ Get a random point coordinates in the defined bounds"""
        point = []
        for bound in self.bounds:
            point.append((np.max(bound) - np.min(bound)) * np.random.random_sample() +
                         np.min(bound))
        return np.array(point)

    def ask(self) -> np.ndarray:
        if self.ini_random_points > 0:
            self.ini_random_points -= 1
            self._next_point = self.get_random_point()
        else:
            self._next_point = self._algo.space.params_to_array(self._algo.suggest(self._utility))
        self._suggested_coordinates.append(self._next_point)
        return self._next_point

    def tell(self, function_value: float):
        self._algo.register(params=self._next_point, target=function_value)

    @property
    def best_fitness(self) -> float:
        return self._algo.max['target']

    @property
    def best_individual(self) -> Union[np.ndarray, None]:
        if self._algo.max is None:
            return None
        else:
            max_param = self._algo.max.get('params', None)
            if max_param is None:
                return None
            return self._algo.space.params_to_array(max_param)

    def stopping(self, ind_iter: int, stopping_parameters: StoppingParameters):
        if ind_iter >= stopping_parameters.niter:
            return True
        if ind_iter > stopping_parameters.npoints and stopping_parameters.stop_type == 'Predict':
            coordinates = np.array(self._suggested_coordinates[-stopping_parameters.npoints:]).T
            return np.all(np.std(coordinates, axis=1)
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


class BayesianModelGeneric(ABC):

    optimisation_algorithm: BayesianAlgorithm = BayesianAlgorithm

    actuators_name: List[str] = []
    detectors_name: List[str] = []

    observables_dim: List[ViewersEnum] = []

    params = []  # to be subclassed

    def __init__(self, optimisation_controller: 'BayesianOptimisation'):
        self.optimisation_controller = optimisation_controller  # instance of the pid_controller using this model
        self.modules_manager: ModulesManager = optimisation_controller.modules_manager

        self.settings = self.optimisation_controller.settings.child('models', 'model_params')  # set of parameters
        self.check_modules(self.modules_manager)

    def check_modules(self, modules_manager):
        for act in self.actuators_name:
            if act not in modules_manager.actuators_name:
                logger.warning(f'The actuator {act} defined in the model is'
                               f' not present in the Dashboard')
                return False
        for det in self.detectors_name:
            if det not in modules_manager.detectors_name:
                logger.warning(f'The detector {det} defined in the model is'
                               f' not present in the Dashboard')

    def update_detector_names(self):
        names = self.optimisation_controller.settings.child(
            'main_settings', 'detector_modules').value()['selected']
        self.data_names = []
        for name in names:
            name = name.split('//')
            self.data_names.append(name)

    def update_settings(self, param: Parameter):
        """
        Get a parameter instance whose value has been modified by a user on the UI
        To be overwritten in child class
        """
        ...

    def update_plots(self):
        """ Called when updating the live plots """
        pass

    def ini_model_base(self):
        self.modules_manager.selected_actuators_name = self.actuators_name
        self.modules_manager.selected_detectors_name = self.detectors_name

        self.ini_model()

    def ini_model(self):
        """ To be subclassed

        Initialize whatever is needed by your custom model
        """
        raise NotImplementedError

    def runner_initialized(self):
        """ To be subclassed

        Initialize whatever is needed by your custom model after the optimization runner is
        initialized
        """
        pass

    def convert_input(self, measurements: DataToExport) -> float:
        """
        Convert the measurements in the units to be fed to the Optimisation Controller
        Parameters
        ----------
        measurements: DataToExport
            data object exported from the detectors from which the model extract a float value
            (fitness) to be fed to the algorithm

        Returns
        -------
        float

        """
        raise NotImplementedError

    def convert_output(self, outputs: List[np.ndarray], best_individual=None) -> DataToActuators:
        """ Convert the output of the Optimisation Controller in units to be fed into the actuators
        Parameters
        ----------
        outputs: list of numpy ndarray
            output value from the controller from which the model extract a value of the same units as the actuators
        best_individual: np.ndarray
            the coordinates of the best individual so far
        Returns
        -------
        DataToActuatorOpti: derived from DataToExport. Contains value to be fed to the actuators with a a mode
            attribute, either 'rel' for relative or 'abs' for absolute.

        """
        raise NotImplementedError


class BayesianModelDefault(BayesianModelGeneric):

    actuators_name: List[str] = []  # to be populated dynamically at instantiation
    detectors_name: List[str] = []  # to be populated dynamically at instantiation

    params = [{'title': 'Optimizing signal', 'name': 'optimizing_signal', 'type': 'group',
                'children': [
                    {'title': 'Get data', 'name': 'data_probe', 'type': 'action'},
                    {'title': 'Optimize 0Ds:', 'name': 'optimize_0d', 'type': 'itemselect',
                     'checkbox': True},
        ]},]

    def __init__(self, optimisation_controller: 'BayesianOptimisation'):
        self.actuators_name = optimisation_controller.modules_manager.actuators_name
        self.detectors_name = optimisation_controller.modules_manager.detectors_name
        super().__init__(optimisation_controller)

        self.settings.child('optimizing_signal', 'data_probe').sigActivated.connect(
            self.optimize_from)

    def ini_model(self):
        pass

    def optimize_from(self):
        self.modules_manager.get_det_data_list()
        data0D = self.modules_manager.settings['data_dimensions', 'det_data_list0D']
        data0D['selected'] = data0D['all_items']
        self.settings.child('optimizing_signal', 'optimize_0d').setValue(data0D)

    def update_settings(self, param: Parameter):
        pass

    def convert_input(self, measurements: DataToExport) -> float:
        """ Convert the measurements in the units to be fed to the Optimisation Controller

        Parameters
        ----------
        measurements: DataToExport
            data object exported from the detectors from which the model extract a float value
            (fitness) to be fed to the algorithm

        Returns
        -------
        float

        """
        data_name: str = self.settings['optimizing_signal', 'optimize_0d']['selected'][0]
        origin, name = data_name.split('/')
        return float(measurements.get_data_from_name_origin(name, origin).data[0][0])

    def convert_output(self, outputs: List[np.ndarray], best_individual=None) -> DataToActuators:
        """ Convert the output of the Optimisation Controller in units to be fed into the actuators
        Parameters
        ----------
        outputs: list of numpy ndarray
            output value from the controller from which the model extract a value of the same units as the actuators
        best_individual: np.ndarray
            the coordinates of the best individual so far

        Returns
        -------
        DataToActuators: derived from DataToExport. Contains value to be fed to the actuators
        with a mode            attribute, either 'rel' for relative or 'abs' for absolute.

        """
        return DataToActuators('outputs', mode='abs',
                               data=[DataActuator(self.modules_manager.actuators_name[ind],
                                                  data=float(outputs[ind])) for ind in
                                     range(len(outputs))])


def get_bayesian_models(model_name=None):
    """
    Get PID Models as a list to instantiate Control Actuators per degree of liberty in the model

    Returns
    -------
    list: list of disct containting the name and python module of the found models
    """
    models_import = []
    discovered_models = get_entrypoints(group='pymodaq.models')
    if len(discovered_models) > 0:
        for pkg in discovered_models:
            try:
                module = importlib.import_module(pkg.value)
                module_name = pkg.value

                for mod in pkgutil.iter_modules([
                    str(Path(module.__file__).parent.joinpath('models'))]):
                    try:
                        model_module = importlib.import_module(f'{module_name}.models.{mod.name}',
                                                               module)
                        classes = inspect.getmembers(model_module, inspect.isclass)
                        for name, klass in classes:
                            if issubclass(klass, BayesianModelGeneric):
                                if find_dict_in_list_from_key_val(models_import, 'name', mod.name)\
                                        is None:
                                    models_import.append({'name': klass.__name__,
                                                          'module': model_module,
                                                          'class': klass})

                    except Exception as e:
                        logger.warning(str(e))

            except Exception as e:
                logger.warning(f'Impossible to import the {pkg.value} bayesian model: {str(e)}')
    if find_dict_in_list_from_key_val(models_import, 'name', 'BayesianModelDefault') \
            is None:
        models_import.append({'name': 'BayesianModelDefault',
                              'module': inspect.getmodule(BayesianModelDefault),
                              'class': BayesianModelDefault})
    if model_name is None:
        return models_import
    else:
        return find_dict_in_list_from_key_val(models_import, 'name', model_name)


class BayesianConfig(BaseConfig):
    """Main class to deal with configuration values for this plugin"""
    config_template_path = None
    config_name = f"bayesian_settings"
