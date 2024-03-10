# -*- coding: utf-8 -*-
"""
Created the 31/08/2023

@author: Sebastien Weber
"""
from abc import ABC, abstractproperty, abstractmethod
from typing import List, TYPE_CHECKING, Union
from pathlib import Path
import importlib
import pkgutil
import inspect
import numpy as np
from qtpy import QtWidgets
import tempfile
from collections import namedtuple

from bayes_opt import BayesianOptimization
from bayes_opt import UtilityFunction


from pymodaq.utils.h5modules.saving import H5Saver
from pymodaq.utils.data import DataToExport, DataActuator, DataToActuators, DataCalculated
from pymodaq.utils.managers.modules_manager import ModulesManager
from pymodaq.utils.daq_utils import find_dict_in_list_from_key_val, get_entrypoints
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.plotting.data_viewers.viewer import ViewersEnum
from pymodaq.utils.enums import BaseEnum
from pymodaq.utils.parameter import Parameter

if TYPE_CHECKING:
    from pymodaq.extensions.bayesian.optimisation import BayesianOptimisation

logger = set_logger(get_module_name(__file__))


class UtilityKind(BaseEnum):
    ucb = 'Upper Confidence Bound'
    ei = 'Expected Improvement'
    poi = 'Probability of Improvement'


UtilityParameters = namedtuple('UtilityParameters',
                               ['kind', 'kappa', 'xi', 'kappa_decay', 'kappa_decay_delay'])


class BayesianAlgorithm:

    def __init__(self, ini_random: int, bounds: dict, **kwargs):

        self._algo = BayesianOptimization(f=None,
                                          pbounds=bounds,
                                          random_state=ini_random,
                                          **kwargs
                                          )

        self._utility = UtilityFunction(kind="ucb", kappa=2.5, xi=0.0)

    def set_utility_function(self, kind: str, **kwargs):
        if kind in UtilityKind.names():
            self._utility = UtilityFunction(kind, **kwargs)

    def ask(self) -> np.ndarray:
        self._next_points = self._algo.space.params_to_array(self._algo.suggest(self._utility))
        return self._next_points

    def tell(self, function_value: float):
        self._algo.register(params=self._next_points, target=function_value)

    @property
    def best_fitness(self) -> float:
        return self._algo.max['target']

    @property
    def best_individual(self) -> Union[np.ndarray, None]:
        max_param = self._algo.max.get('params', None)
        if max_param is None:
            return None
        return self._algo.space.params_to_array(max_param)


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

    def __init__(self, optimisation_controller: 'Optimisation'):
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
