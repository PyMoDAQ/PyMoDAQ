# -*- coding: utf-8 -*-
"""
Created the 31/08/2023

@author: Sebastien Weber
"""
import abc
from abc import ABC
from typing import List, TYPE_CHECKING, Union, Dict, Tuple, Iterable
from pathlib import Path
import importlib
import pkgutil
import inspect
import numpy as np
from collections import namedtuple

from pymodaq_utils.abstract import abstract_attribute
from pymodaq_utils.utils import find_dict_in_list_from_key_val, get_entrypoints
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_utils.enums import BaseEnum
from pymodaq_utils.config import BaseConfig

from pymodaq_gui.plotting.data_viewers.viewer import ViewersEnum
from pymodaq_gui.managers.parameter_manager import Parameter


from pymodaq_data.data import (DataToExport, DataCalculated,
                                DataRaw, Axis)

from pymodaq.utils.data import DataActuator, DataToActuators
from pymodaq.utils.managers.modules_manager import ModulesManager


logger = set_logger(get_module_name(__file__))


class StopType(BaseEnum):
    Predict = 0


StoppingParameters = namedtuple('StoppingParameters',
                                ['niter', 'stop_type', 'tolerance', 'npoints'])


class GenericAlgorithm(abc.ABC):

    def __init__(self, ini_random: int):

        self._algo = abstract_attribute()  #could be a Bayesian on Adapative algorithm
        self._prediction = abstract_attribute()  # could be an acquisition function...

        self._next_point: np.ndarray = None
        self._suggested_coordinates: List[np.ndarray] = []
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
    def bounds(self) -> List[np.ndarray]:
        pass

    @bounds.setter
    def bounds(self, bounds: Union[Dict[str, Tuple[float, float]], Iterable[np.ndarray]]):
        if isinstance(bounds, dict):
            self._algo.set_bounds(bounds)
        else:
            self._algo.set_bounds(self._algo.space.array_to_params(np.array(bounds)))

    def get_random_point(self) -> np.ndarray:
        """ Get a random point coordinates in the defined bounds"""
        point = []
        for bound in self.bounds:
            point.append((np.max(bound) - np.min(bound)) * np.random.random_sample() +
                         np.min(bound))
        return np.array(point)

    def ask(self) -> list[np.ndarray]:
        """ Predict next actuator values to probe

        Return a list of numpy array, one per actuator. In general these array are 0D
        """
        try:
            self._next_point = self.prediction_ask()
        except:
            self.ini_random_points -= 1
            self._next_point = self.get_random_point()
        self._suggested_coordinates.append(self._next_point)
        return [np.atleast_1d(value) for value in self._next_point]

    @abc.abstractmethod
    def prediction_ask(self) -> np.ndarray:
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
    def best_individual(self) -> Union[np.ndarray, None]:
        pass

    @abc.abstractmethod
    def stopping(self, ind_iter: int, stopping_parameters: StoppingParameters) -> bool:
        pass


class OptimizerModelGeneric(ABC):

    optimization_algorithm: GenericAlgorithm = None

    actuators_name: List[str] = []
    detectors_name: List[str] = []

    observables_dim: List[ViewersEnum] = []

    params = []  # to be subclassed

    def __init__(self, optimization_controller):
        self.optimization_controller = optimization_controller  # instance of the pid_controller using this model
        self.modules_manager: ModulesManager = optimization_controller.modules_manager

        self.settings = self.optimization_controller.settings.child('models', 'model_params')  # set of parameters
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
        names = self.optimization_controller.settings.child(
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


class OptimizerModelDefault(OptimizerModelGeneric):

    actuators_name: List[str] = []  # to be populated dynamically at instantiation
    detectors_name: List[str] = []  # to be populated dynamically at instantiation

    params = [{'title': 'Optimizing signal', 'name': 'optimizing_signal', 'type': 'group',
               'children': [
                   {'title': 'Get data', 'name': 'data_probe', 'type': 'action'},
                   {'title': 'Optimize 0Ds:', 'name': 'optimize_0d', 'type': 'itemselect',
                    'checkbox': True},
               ]},]

    def __init__(self, optimization_controller):
        self.actuators_name = optimization_controller.modules_manager.actuators_name
        self.detectors_name = optimization_controller.modules_manager.detectors_name
        super().__init__(optimization_controller)

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
        return DataToActuators(
            'outputs', mode='abs',
            data=[DataActuator(self.modules_manager.actuators_name[ind],
                               data=float(outputs[ind][0])) for ind in  range(len(outputs))])




def get_optimizer_models(model_name=None):
    """
    Get Optimizer Models as a list to instantiate Control Actuators per degree of liberty in the model

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
                            if issubclass(klass, OptimizerModelGeneric):
                                if find_dict_in_list_from_key_val(models_import, 'name', mod.name)\
                                        is None:
                                    models_import.append({'name': klass.__name__,
                                                          'module': model_module,
                                                          'class': klass})

                    except Exception as e:
                        logger.warning(str(e))

            except Exception as e:
                logger.warning(f'Impossible to import the {pkg.value} optimizer model: {str(e)}')

    if find_dict_in_list_from_key_val(models_import, 'name', 'OptimizerModelDefault') \
            is None:
        models_import.append({'name': 'OptimizerModelDefault',
                              'module': inspect.getmodule(OptimizerModelDefault),
                              'class': OptimizerModelDefault})
    if model_name is None:
        return models_import
    else:
        return find_dict_in_list_from_key_val(models_import, 'name', model_name)


class OptimizerConfig(BaseConfig):
    """Main class to deal with configuration values for this plugin

    To b subclassed for real implementation if needed, see Optimizer class attribute config_saver
    """
    config_template_path = None
    config_name = f"optimizer_settings"


def find_key_in_nested_dict(dic, key):
    stack = [dic]
    while stack:
        d = stack.pop()
        if key in d:
            return d[key]
        for v in d.values():
            if isinstance(v, dict):
                stack.append(v)
            if isinstance(v, list):
                stack += v
