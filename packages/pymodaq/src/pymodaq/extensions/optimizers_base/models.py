import abc
import importlib
import inspect
import pkgutil
from abc import ABC
from pathlib import Path
from typing import List, Union, Optional

import numpy as np
from pyqtgraph.parametertree import Parameter

from pymodaq.extensions.optimizers_base.utils import logger, individual_as_dta
from pymodaq.extensions.optimizers_base.algorithm import GenericAlgorithm
from pymodaq.utils.data import DataToActuators
from pymodaq.utils.managers.modules_manager import ModulesManager
from pymodaq_data import DataToExport
from pymodaq_gui.plotting.data_viewers import ViewersEnum
from pymodaq_utils.utils import get_entrypoints, find_dict_in_list_from_key_val


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

    @abc.abstractmethod
    def has_fitness_observable(self) -> bool:
        """ Should return True if the model defined a 0D data to be used as fitness value"""
        return False

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

    def convert_output(self, outputs: dict[str, Union[float, np.ndarray]],
                       best_individual: Optional[dict[str, float]] = None) -> DataToActuators:
        """ Convert the output of the Optimisation Controller in units to be fed into the actuators
        Parameters
        ----------
        outputs: dict with name of the actuator as key and the value to move to as a float (or ndarray)
            output value from the controller from which the model extract a value of the same units as the actuators
        best_individual: dict[str, float]
            the coordinates of the best individual so far
        Returns
        -------
        DataToActuatorOpti: derived from DataToExport. Contains value to be fed to the actuators with a 'mode'
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
        self.actuators_name = optimization_controller.modules_manager.selected_actuators_name
        self.detectors_name = optimization_controller.modules_manager.selected_detectors_name
        super().__init__(optimization_controller)

        self.settings.child('optimizing_signal', 'data_probe').sigActivated.connect(
            self.optimize_from)

    def has_fitness_observable(self) -> bool:
        """ Should return True if the model defined a 0D data to be used as fitness value"""
        return len(self.settings.child('optimizing_signal', 'optimize_0d').value()['selected']) == 1

    def ini_model(self):
        pass

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

    def convert_output(self, outputs: dict[str, Union[float, np.ndarray]],
                       best_individual: Optional[dict[str, float]] = None) -> DataToActuators:
        """ Convert the output of the Optimisation Controller in units to be fed into the actuators
        Parameters
        ----------
        outputs: dict with name of the actuator as key and the value to move to as a float (or ndarray)
            output value from the controller from which the model extract a value of the same units as the actuators
        best_individual: dict[str, float]
            the coordinates of the best individual so far
        Returns
        -------
        DataToActuatorOpti: derived from DataToExport. Contains value to be fed to the actuators with a 'mode'
            attribute, either 'rel' for relative or 'abs' for absolute.

        """
        return individual_as_dta(outputs, self.modules_manager.actuators, 'outputs', mode='abs')

    def optimize_from(self):
        self.modules_manager.get_det_data_list()
        data0D_names = self.modules_manager.get_probed_data_channels('Data0D')
        self.settings.child('optimizing_signal', 'optimize_0d').setValue(
            dict(all_items=data0D_names, selected=data0D_names))


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

    if find_dict_in_list_from_key_val(models_import, 'name', 'OptimizerModelDefault')  is None:
        models_import.append({'name': 'OptimizerModelDefault',
                              'module': inspect.getmodule(OptimizerModelDefault),
                              'class': OptimizerModelDefault})
    if model_name is None:
        return models_import
    else:
        return find_dict_in_list_from_key_val(models_import, 'name', model_name)
