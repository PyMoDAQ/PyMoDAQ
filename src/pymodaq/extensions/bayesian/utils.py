# -*- coding: utf-8 -*-
"""
Created the 31/08/2023

@author: Sebastien Weber
"""
from abc import ABC, abstractproperty, abstractmethod
from typing import List
from pathlib import Path
import importlib
import pkgutil
import inspect
import numpy as np
from qtpy import QtWidgets
import tempfile


from bayes_opt import BayesianOptimization
from bayes_opt import UtilityFunction


from pymodaq.utils.h5modules.saving import H5Saver
from pymodaq.utils.data import DataToExport, DataActuator, DataToActuators, DataCalculated
from pymodaq.utils.managers.modules_manager import ModulesManager
from pymodaq.utils.daq_utils import find_dict_in_list_from_key_val, get_entrypoints
from pymodaq.utils.logger import set_logger, get_module_name
from pymodaq.utils.plotting.data_viewers.viewer import ViewersEnum
from pymodaq.utils.parameter import Parameter
from pymodaq.utils import gui_utils as gutils
from pymodaq.utils.plotting.data_viewers.viewer import ViewerDispatcher
from pymodaq.utils.h5modules import data_saving
from pymodaq.post_treatment.load_and_plot import LoaderPlotter


logger = set_logger(get_module_name(__file__))


class BayesianAlgorithm:

    def __init__(self, ini_random: int, bounds: dict, **kwargs):

        self._algo = BayesianOptimization(f=None,
                                          pbounds=bounds,
                                          random_state=ini_random,
                                          **kwargs
                                          )

        self._utility = UtilityFunction(kind="ucb", kappa=2.5, xi=0.0)

    def ask(self) -> np.ndarray:
        self._next_points = self._algo.space.params_to_array(self._algo.suggest(self._utility))
        return self._next_points

    def tell(self, function_value: float):
        self._algo.register(params=self._next_points, target=function_value)

    @property
    def best_fitness(self) -> float:
        return self._algo.max['target']

    @property
    def best_individual(self) -> np.ndarray:
        return self._algo.space.params_to_array(self._algo.max['params'])


class BayesianModelGeneric(ABC):

    optimisation_algorithm: BayesianAlgorithm = BayesianAlgorithm

    actuators_name: List[str] = []
    detectors_name: List[str] = []

    observables_dim: List[ViewersEnum] = []

    params = []  # to be subclassed

    def __init__(self, optimisation_controller: 'Optimisation'):
        self.optimisation_controller = optimisation_controller  # instance of the pid_controller using this model
        self.modules_manager: ModulesManager = optimisation_controller.modules_manager

        self.settings = self.optimisation_controller.settings.child('models', 'model_params')  # set of parameters
        self.check_modules(self.modules_manager)

        self.h5temp: H5Saver = None
        self.temp_path: tempfile.TemporaryDirectory = None
        self.enlargeable_saver: data_saving.DataToExportExtendedSaver = None
        self.live_plotter = LoaderPlotter(self.optimisation_controller.dockarea)

    def ini_temp_file(self):
        if self.temp_path is not None:
            try:
                self.h5temp.close()
                self.temp_path.cleanup()
            except Exception as e:
                logger.exception(str(e))

        self.h5temp = H5Saver()
        self.temp_path = tempfile.TemporaryDirectory(prefix='pymo')
        addhoc_file_path = Path(self.temp_path.name).joinpath('temp_data.h5')
        self.h5temp.init_file(custom_naming=True, addhoc_file_path=addhoc_file_path)
        self.enlargeable_saver = \
            data_saving.DataToExportEnlargeableSaver(self.h5temp, axis_name='nav axis',
                                                     axis_units='')
        self.live_plotter.h5saver = self.h5temp

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

    def ini_model(self):
        self.modules_manager.selected_actuators_name = self.actuators_name
        self.modules_manager.selected_detectors_name = self.detectors_name

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

    def convert_output(self, outputs: List[np.ndarray]) -> DataToActuators:
        """ Convert the output of the Optimisation Controller in units to be fed into the actuators
        Parameters
        ----------
        outputs: list of numpy ndarray
            output value from the controller from which the model extract a value of the same units as the actuators

        Returns
        -------
        DataToActuatorOpti: derived from DataToExport. Contains value to be fed to the actuators with a a mode
            attribute, either 'rel' for relative or 'abs' for absolute.

        """
        raise NotImplementedError


class BayesianModelDefault(BayesianModelGeneric):

    actuators_name: List[str] = []  # to be populated dynamically at instantiation
    detectors_name: List[str] = []  # to be populated dynamically at instantiation
    observables_dim: List[ViewersEnum] = []

    params = [{'title': 'Optimizing signal', 'name': 'optimizing_signal', 'type': 'group',
                'children': [
                    {'title': 'Get data', 'name': 'data_probe', 'type': 'bool_push'},
                    {'title': 'Optimize 0Ds:', 'name': 'optimize_0d', 'type': 'itemselect',
                     'checkbox': True},
        ]},]

    def __init__(self, optimisation_controller: 'Optimisation'):
        self.actuators_name = optimisation_controller.modules_manager.actuators_name
        self.detectors_name = optimisation_controller.modules_manager.detectors_name
        super().__init__(optimisation_controller)



    def ini_model(self):
        pass

    def optimize_from(self):
        self.modules_manager.get_det_data_list()
        data0D = self.modules_manager.settings['data_dimensions', 'det_data_list0D']
        data0D['selected'] = data0D['all_items']
        self.settings.child('optimizing_signal', 'optimize_0d').setValue(data0D)

    def update_settings(self, param: Parameter):
        if param.name() == 'data_probe':
            self.optimize_from()

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

    def convert_output(self, outputs: List[np.ndarray]) -> DataToActuators:
        """ Convert the output of the Optimisation Controller in units to be fed into the actuators
        Parameters
        ----------
        outputs: list of numpy ndarray
            output value from the controller from which the model extract a value of the same units
            as the actuators

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

                for mod in pkgutil.iter_modules([str(Path(module.__file__).parent.joinpath('models'))]):
                    try:
                        model_module = importlib.import_module(f'{module_name}.models.{mod.name}', module)
                        classes = inspect.getmembers(model_module, inspect.isclass)
                        for name, klass in classes:
                            if isinstance(klass.__name__, BayesianModelGeneric):
                                models_import.append({'name': mod.name, 'module': model_module, 'class': klass})
                                break

                    except Exception as e:  # pragma: no cover
                        logger.warning(str(e))

            except Exception as e:  # pragma: no cover
                logger.warning(f'Impossible to import the {pkg.value} extension: {str(e)}')

    models_import.append({'name': 'BayesianModelDefault',
                          'module': inspect.getmodule(BayesianModelDefault),
                          'class': BayesianModelDefault})

    if model_name is None:
        return models_import
    else:
        return find_dict_in_list_from_key_val(models_import, 'name', model_name)
